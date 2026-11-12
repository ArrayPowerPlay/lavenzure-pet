"""Performance check (roadmap Phase 12): run the pet for a while and record what it costs the PC.

Starts the real app (or attaches to a pet that is already running with ``--pid``), then every few
seconds samples, for that one process:

- CPU, as "% of the whole machine" (the number Task Manager shows),
- RAM (private bytes = memory only this process uses),
- Windows handles, GDI and USER objects (these only ever climbing = a leak),
- GPU 3D-engine use (Windows performance counters, read through PowerShell).

Every sample goes to a CSV file; at the end a summary is printed: averages, peaks, and how fast
RAM / handles grew per hour after a warm-up minute (steady growth hints at a leak). The pet also
writes its own "frame stats" lines (fps, milliseconds per frame) into its log; the summary repeats
the ones written during the run.

Windows only, run with the Windows venv::

    .venv-win/Scripts/python.exe src/perf_check.py --minutes 60
    .venv-win/Scripts/python.exe src/perf_check.py --minutes 10 --pid 12345  # running pet
"""
from __future__ import annotations

import argparse
import csv
import ctypes
import os
import statistics
import subprocess
import sys
import time
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path

import psutil

import app_logging

SRC_DIR = Path(__file__).resolve().parent
WARMUP_SECONDS = 60  # ignore start-up allocations when judging RAM / handle growth
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
GR_GDIOBJECTS, GR_USEROBJECTS = 0, 1


@dataclass
class Sample:
    """One measurement of the pet process."""

    elapsed_s: float
    cpu_pct: float        # % of the whole machine (all cores = 100 %)
    private_mb: float
    working_set_mb: float
    threads: int
    handles: int
    gdi_objects: int
    user_objects: int
    gpu_3d_pct: float     # -1 when the GPU counters could not be read


def gui_resources(pid: int) -> tuple[int, int]:
    """Number of GDI and USER objects the process owns (-1, -1 if they can't be read)."""
    kernel32, user32 = ctypes.windll.kernel32, ctypes.windll.user32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return -1, -1
    try:
        return (user32.GetGuiResources(handle, GR_GDIOBJECTS),
                user32.GetGuiResources(handle, GR_USEROBJECTS))
    finally:
        kernel32.CloseHandle(handle)


def gpu_3d_percent(pid: int) -> float:
    """Current 3D-engine use of the process in % (sum over its GPU engines), -1 on failure."""
    command = (
        f'$s = (Get-Counter "\\GPU Engine(pid_{pid}_*engtype_3D)\\Utilization Percentage" '
        "-ErrorAction SilentlyContinue).CounterSamples; "
        "if ($s) { ($s | Measure-Object CookedValue -Sum).Sum } else { 0 }"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", command],
            capture_output=True, text=True, timeout=20,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return float(result.stdout.strip().replace(",", ".") or 0)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return -1.0


def real_process(proc: psutil.Process) -> psutil.Process:
    """The process that actually runs the pet.

    A venv's ``python.exe`` is a small launcher that starts the real interpreter as a child, so
    the launched process itself uses almost nothing; follow it down to its last child.
    """
    while True:
        children = proc.children()
        if not children:
            return proc
        proc = children[0]


def take_sample(proc: psutil.Process, started: float, with_gpu: bool) -> Sample:
    """Measure ``proc`` now. CPU % covers the time since the previous call."""
    with proc.oneshot():
        cpu = proc.cpu_percent(None) / psutil.cpu_count()
        mem = proc.memory_info()
        threads = proc.num_threads()
        handles = proc.num_handles()
    gdi, user = gui_resources(proc.pid)
    gpu = gpu_3d_percent(proc.pid) if with_gpu else -1.0
    return Sample(
        elapsed_s=round(time.monotonic() - started, 1),
        cpu_pct=round(cpu, 2),
        private_mb=round(getattr(mem, "private", mem.rss) / 2**20, 1),
        working_set_mb=round(mem.rss / 2**20, 1),
        threads=threads, handles=handles, gdi_objects=gdi, user_objects=user,
        gpu_3d_pct=round(gpu, 2),
    )


def per_hour_growth(samples: list[Sample], attr: str) -> float:
    """Least-squares slope of ``attr`` over time after the warm-up, in units per hour."""
    points = [(s.elapsed_s, getattr(s, attr)) for s in samples if s.elapsed_s >= WARMUP_SECONDS]
    if len(points) < 3:
        return 0.0
    slope = statistics.linear_regression([p[0] for p in points], [p[1] for p in points]).slope
    return slope * 3600


def percentile(values: list[float], pct: float) -> float:
    """The ``pct``-th percentile of ``values`` (nearest rank)."""
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(pct / 100 * (len(ordered) - 1))))]


def summarize(samples: list[Sample], frame_lines: list[str]) -> str:
    """Human-readable report of a finished run."""
    cpu = [s.cpu_pct for s in samples[1:]] or [0.0]  # the first CPU reading is always 0
    gpu = [s.gpu_3d_pct for s in samples if s.gpu_3d_pct >= 0]
    first, last = samples[0], samples[-1]
    lines = [
        f"Duration: {last.elapsed_s / 60:.1f} min, {len(samples)} samples",
        f"CPU (% of whole PC): avg {statistics.mean(cpu):.2f}, "
        f"95th pct {percentile(cpu, 95):.2f}, max {max(cpu):.2f}",
        f"RAM private: {first.private_mb:.0f} -> {last.private_mb:.0f} MB "
        f"(max {max(s.private_mb for s in samples):.0f}), "
        f"growth after warm-up {per_hour_growth(samples, 'private_mb'):+.1f} MB/hour",
        f"Handles: {first.handles} -> {last.handles} "
        f"({per_hour_growth(samples, 'handles'):+.0f}/hour), "
        f"GDI {first.gdi_objects} -> {last.gdi_objects}, "
        f"USER {first.user_objects} -> {last.user_objects}, threads {last.threads}",
    ]
    if gpu:
        lines.append(f"GPU 3D engine: avg {statistics.mean(gpu):.1f} %, max {max(gpu):.1f} %")
    else:
        lines.append("GPU 3D engine: not available")
    if frame_lines:
        lines.append("Frame stats from the pet's log:")
        lines.extend(f"  {line}" for line in frame_lines)
    return "\n".join(lines)


def read_frame_stats(log_file: Path, since: datetime) -> list[str]:
    """``frame stats`` lines the pet wrote to its log after ``since``."""
    if not log_file.exists():
        return []
    found = []
    for line in log_file.read_text(encoding="utf-8", errors="replace").splitlines():
        if "frame stats:" not in line:
            continue
        try:
            stamp = datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if stamp >= since.replace(microsecond=0):
            found.append(f"{line[11:19]} {line.split('frame stats:', 1)[1].strip()}")
    return found


def running_pets() -> list[psutil.Process]:
    """Pet processes that are already running (any ``python*`` started with ``main.py``)."""
    found = []
    for proc in psutil.process_iter(["name", "cmdline"]):
        name = (proc.info["name"] or "").lower()
        cmdline = " ".join(proc.info["cmdline"] or [])
        if name.startswith("python") and "main.py" in cmdline:
            found.append(proc)
    return found


def launch_pet(frame_stats_seconds: int) -> subprocess.Popen:
    """Start ``main.py`` with the same interpreter; frame stats are logged more often."""
    env = dict(os.environ, CALCIFER_FRAME_STATS_SECONDS=str(frame_stats_seconds))
    return subprocess.Popen([sys.executable, str(SRC_DIR / "main.py")], cwd=SRC_DIR.parent,
                            env=env)


def stop_pet(child: subprocess.Popen, proc: psutil.Process) -> None:
    """Close the pet this script launched: the real interpreter first, then the launcher."""
    for target in (proc, psutil.Process(child.pid) if child.poll() is None else None):
        if target is None:
            continue
        try:
            target.terminate()
            target.wait(10)
        except psutil.Error:
            pass


def parse_args() -> argparse.Namespace:
    """Command-line options."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--minutes", type=float, default=60, help="how long to measure")
    parser.add_argument("--interval", type=float, default=10, help="seconds between samples")
    parser.add_argument("--pid", type=int, help="measure an already running pet instead")
    parser.add_argument("--no-gpu", action="store_true", help="skip the (slower) GPU counters")
    parser.add_argument("--keep", action="store_true",
                        help="leave the launched pet running afterwards")
    parser.add_argument("--csv", type=Path, help="where to write the samples")
    return parser.parse_args()


def main() -> int:
    """Launch or attach, sample until the time is up (or the pet exits), then report."""
    if sys.platform != "win32":
        print("perf_check.py measures the real Windows app; run it with .venv-win.")
        return 2
    args = parse_args()
    since = datetime.now()
    child = None
    if args.pid:
        proc = psutil.Process(args.pid)
    else:
        already = running_pets()
        if already:
            # A second start would only open the running pet's chat (single instance).
            pids = ", ".join(str(real_process(p).pid) for p in already if not p.parent()
                             or "main.py" not in " ".join(p.parent().cmdline()))
            print(f"A pet is already running (pid {pids}). Quit it from the tray first, "
                  "or measure it with --pid.")
            return 1
        child = launch_pet(frame_stats_seconds=max(30, int(args.minutes * 60 / 6)))
        time.sleep(5)
        if child.poll() is not None:
            print("The pet exited right away - is another pet already running? "
                  "Quit it or pass --pid <its process id>.")
            return 1
        proc = real_process(psutil.Process(child.pid))

    csv_path = args.csv or app_logging.log_dir() / f"perf_{since:%Y%m%d_%H%M%S}.csv"
    samples: list[Sample] = []
    started = time.monotonic()
    proc.cpu_percent(None)  # prime the CPU counter
    print(f"Measuring pid {proc.pid} for {args.minutes:g} min -> {csv_path}")
    try:
        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow([f.name for f in fields(Sample)])
            while time.monotonic() - started < args.minutes * 60:
                time.sleep(args.interval)
                sample = take_sample(proc, started, with_gpu=not args.no_gpu)
                samples.append(sample)
                writer.writerow([getattr(sample, f.name) for f in fields(Sample)])
                fh.flush()
                print(f"\r{sample.elapsed_s / 60:5.1f} min  cpu {sample.cpu_pct:5.2f}%  "
                      f"ram {sample.private_mb:6.1f} MB  gpu {sample.gpu_3d_pct:5.1f}%",
                      end="", flush=True)
    except psutil.NoSuchProcess:
        print("\nThe pet process ended during the measurement.")
    except KeyboardInterrupt:
        print("\nStopped early.")
    finally:
        if child is not None and not args.keep:
            stop_pet(child, proc)
    print()
    if not samples:
        print("No samples taken.")
        return 1
    print(summarize(samples, read_frame_stats(app_logging.log_dir() / "calcifer.log", since)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
