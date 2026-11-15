# CLAUDE.md

Guidance for Claude Code (claude.ai/code) when working in this repository.

## Project

Lavenzure: a Calcifer-style desktop pet for **Windows only, single monitor**, released publicly for free (non-commercial; user decision 2026-11-15, so the old "personal use only" rule is gone). The app and the pet are always called **Lavenzure**: Calcifer is only the reference character, never use that name for the product, files or releases. Never use original film assets (the character is drawn entirely in code). A flame character lives in an always-on-top transparent window, wanders around the screen, reacts to clicks/drags, and opens a chat bubble (right-click menu → Chat) backed by a tool-calling LangGraph agent on Gemini or OpenAI (the user picks in Settings).

The user writes Vietnamese. Everything the pet says on screen (care lines, facts/jokes, alerts, reminders) exists in **English and Vietnamese** and follows Settings → Language (`src/pet_lines.py`): any new on-screen pet text needs both versions. Code, comments and docstrings stay English; chat replies follow the language the user writes in.

## Docs and skills

Design docs are in Vietnamese. Read the relevant one before changing behavior and update it when a decision changes:
- `docs/DECISION_LOG.md` — dated log of decisions agreed with the user, plus open questions. **Append to it whenever a decision is made.** It is the source of truth for "why is it like this".
- `docs/implementation_plan.md` — phase checklist, current status and the A-H roadmap.
- `docs/TASKS.md` — ideas that are pending, researched or rejected (do not re-propose rejected ones).
- `docs/TEST_CHECKLIST.md` — manual checks on the real desktop; `docs/ANIMATION_TUTORIAL.md` — superseded PNG-cutout plan, reference only.

**Animation work** (moods, faces, props, click reactions, body motion, the flame): use the `pet-animation` skill (`.claude/skills/pet-animation/`). It holds how the character is drawn, the art direction the user approved or rejected, the add-a-mood / add-a-prop / copy-a-reference workflows and the render scripts. Graphics details deliberately live there, not here.

## Locked decisions

- **Window**: ordinary always-on-top transparent overlay (no WorkerW desktop-layer trick). Click-through relies on Windows per-pixel-alpha hit-testing of the layered window: never add `setMask()` (it clips the glow/embers) and keep the glow fading to alpha 0. The chat bubble is always-on-top too; only the overlay is click-through.
- **Process**: one process, one `QApplication`; the agent runs in its own `QThread`, never on the UI thread. Only one pet runs (`single_instance.py`: a second start opens the first one's chat and exits).
- **LLM**: Gemini (`langchain-google-genai`) or OpenAI (`langchain-openai`, model `llm.openai_model`), chosen in Settings → Chat AI (`user_settings` `provider`, default `llm.provider`); called directly (not OpenRouter); agent framework is LangGraph (not Google ADK). Chat history is RAM-only, wiped after `memory.idle_timeout_minutes` (15) — no persistence by design.
- **System alerts**: battery < 30 %, CPU > 90 %, RAM > 90 % (`system_status` in `config.yaml`) → alert face + sticky bubble that stays until the user clicks the pet, then the pet stays quiet for `snooze_minutes` (10).
- **Ambient lines** (care lines, facts/jokes) are pet behavior in the monitor, **not** an LLM tool.
- **Look and performance**: character scale 0.75; 30 fps default (Settings offers 30/60); `shader` flame renderer (user's choice); lite flame always on (user's choice); soft glow kept, no white sticker border.
- **Autostart**: a "Start with Windows" switch in Settings, **off by default**; it writes/removes the `HKCU\...\Run` value via `winreg` (`src/autostart/startup.py`; no Task Scheduler, no admin, no `pywin32`). It also honours the switch in Task Manager (`StartupApproved`).
- **Release** (v0.1.0; decisions in `docs/DECISION_LOG.md` lượt 34, steps in `implementation_plan.md` phase F): Windows only, macOS later. `Lavenzure.exe` from PyInstaller `--onedir --windowed` (`lavenzure.spec`, `scripts/build.py`), built on Windows, shipped as `Lavenzure-<ver>-win-x64.zip` + SHA256 (no installer, no code signing yet). SemVer from git tags (`vX.Y.Z`, `-rc.N` for trials; trunk-based: only tags on `main` publish; other branches get `.devN+sha`); `src/version.py` reads the tag, and `scripts/write_version.py` writes the git-ignored `src/_version.py` at build time; never edit a version by hand. `.github/workflows/release.yml` runs lint + tests + build + GitHub Release on a `v*` tag push. Read-only bundled files (`config.yaml`, `data/`, `assets/`) are found with `paths.resource(...)` (works from source and from the package); user data stays in `%LOCALAPPDATA%\Lavenzure`.
- **API keys** (`src/api_keys.py`, `ui/api_key_panel.py`, `agent/key_check.py`): Gemini / OpenAI / Tavily keys are typed in Settings, checked against the service on a worker thread, saved ONLY when valid, in `keyring` (service `Lavenzure`; no plaintext fallback). Keys are read when needed, never at import time, so a new key works without a restart (`graph.reset_agent()`); env vars / `.env` (dev only) override saved keys. Never log a key or put it in a URL.

## Environment & commands

The repo is on the Windows drive: `D:\workspace\Repo\pet` (WSL: `/mnt/d/workspace/Repo/pet`). A stale copy under the WSL home may exist; ignore it. Two venvs, both git-untracked:

- `.venv-win` — **Windows** Python 3.13 with PySide6. Use it for the real app (run from WSL; windows open on the Windows desktop), tests and scripts.
- `.venv` — **Linux** Python 3.12, only for rough WSLg previews. Transparency / always-on-top / click-through differ there, so never judge overlay behavior with it.

```bash
.venv-win/Scripts/python.exe src/main.py                              # run the app
UV_PROJECT_ENVIRONMENT=.venv-win WSLENV=UV_PROJECT_ENVIRONMENT uv.exe sync --frozen   # install exactly what uv.lock says into .venv-win
QT_QPA_PLATFORM=offscreen .venv-win/Scripts/python.exe src/main.py    # headless smoke test
.venv-win/Scripts/python.exe -m pytest                                # headless test suite
.venv-win/Scripts/python.exe -m ruff check .                          # lint (config in pyproject.toml)
.venv-win/Scripts/python.exe src/character_preview.py [renderer ...]  # try every mood/motion in a window
.venv-win/Scripts/python.exe src/perf_check.py --minutes 60           # CPU/RAM/GPU of the real app (quit the pet first)
.venv-win/Scripts/python.exe src/desktop_check.py                     # read-only on-top / click-through checks of the running pet
.venv-win/Scripts/python.exe src/reminder_check.py [--repeat N]       # reminder cases vs the REAL model (run after any system-prompt change)
.venv-win/Scripts/python.exe src/bake_flame.py                        # re-run the offline fire sim for the `baked` renderer
.venv-win/Scripts/python.exe scripts/build.py [version]                # build dist/Lavenzure-<ver>-win-x64.zip (takes minutes; run in the background)
```

- **Dependencies are managed by uv**: they are declared in `pyproject.toml` (`dependencies`, and the `dev` group with pytest, ruff, pyinstaller) and locked in `uv.lock`; there is no `requirements.txt`. Add one with `uv.exe add <pkg>` (same env vars as above) and commit both files; never `pip install` into the venv. A fresh clone just runs `uv sync` (default venv `.venv`); on this machine the venv is `.venv-win` via `UV_PROJECT_ENVIRONMENT`. Python is pinned by `.python-version` (3.13) / `requires-python`. Do not `uv sync` while the pet runs from that venv (Windows locks the loaded `.pyd` files). CI uses `uv sync --frozen`.
- `.venv-win/Scripts/*.exe` giving "Permission denied" from WSL after recreating the venv: `chmod +x .venv-win/Scripts/*.exe`.
- `src/` is the import root (`import config`, `from overlay.x import ...`, no `src.` prefix). Run scripts as `src/main.py`; in scratch scripts `sys.path.insert` the `src` dir (`PYTHONPATH` is not forwarded to Windows Python). Env vars only reach it through `WSLENV`, e.g. `QT_QPA_PLATFORM=offscreen WSLENV=QT_QPA_PLATFORM ...`.
- Tests are headless (`tests/conftest.py` sets `QT_QPA_PLATFORM=offscreen` and fakes network/psutil). The release build is `scripts/build.py`.
- Keys: normally entered in Settings (see **API keys** above). For development copy `.env.example` → `.env` (`GEMINI_API_KEY`, `OPENAI_API_KEY`, `TAVILY_API_KEY`); tests never touch the real key store (`tests/conftest.py` fakes `keyring` and clears the key env vars). Other settings are in `config.yaml`, read with `config.get("dotted.path", default)`. The chat model is built lazily on the first chat message, so the app starts without a key. Gemini model `gemini-flash-lite-latest` (no thinking; `gemini-flash-latest` took 4-8 s per reply) on the `v1beta` endpoint — `-latest` aliases do not exist on `v1`.
- Logs: `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log` (rotating, includes uncaught exceptions). User settings (language, outfit, fps) and reminders also live in `%LOCALAPPDATA%\Lavenzure\`.
- Line endings are mixed (most `src/overlay/*.py` are CRLF, many others LF; git stores LF via `.gitattributes`). Keep each file's endings; a whole-file diff with no real change is a line-ending flip.

## Architecture

`src/main.py` (`LavenzureApp`) builds every component and wires them with Qt signals; components don't reference each other directly, so trace behavior through `_wire_signals`.

- **Overlay** (`src/overlay/`)
  - `character.py` `FlameCharacter` — the pet, drawn entirely in code. A plain model+renderer, not a widget: `update(dt, window_pos, cursor)` then `paint(painter)`. Body language is **derived from the window's own movement**, so movement code never animates the body directly. Mood layering: transient `play(mood, seconds)` > alert > reminding > sleeping > thinking > riding the log > normal. Its parts are `face.py` (expressions as `Expression` data), `props.py`, `flame_*.py` / `fire_field.py` (flame renderers). **Details: `pet-animation` skill.**
  - `overlay_window.py` `OverlaySprite` — frameless, translucent, `WindowStaysOnTopHint | Tool`; runs the frame timer. Keeps a float position: move it with `set_exact_pos`, not `move`. Emits `clicked`, `drag_started`/`drag_ended` (after a 6 px threshold), `right_clicked`.
  - `behavior.py` `BehaviorController` — `PetState` machine (random IDLE/WALK/FLOAT/JUMP loop weighted by `behavior.state_weights`; overrides resolved in `_resume()`: dragging > alert > reminding > reacting > chatting > resting/dozing > wandering). Left-click reactions are methods decorated `@reaction("name")`: defining one adds it to the click pool. Moves the *whole window* (`animation.py`). Uses restartable single-shot `QTimer`s, not `QTimer.singleShot`, so stale timeouts can't double-advance the loop.
  - `speech_bubble.py` — separate top-level window following the pet via an anchor callback; `auto_hide_ms=None` = sticky (alerts, reminders). Jokes/short replies never replace a sticky bubble; while the pet is hidden `LavenzureApp._say` uses a tray notification.
- **Chat** (`src/chat/chat_bubble.py`) — bubble attached to the pet; tabs **Chat | Reminders** (the Reminders tab mirrors the monitor's list and emits cancel requests). Closes itself after `chat.auto_close_seconds` of silence. User text is inserted escaped; replies are rendered from Markdown. Each reply starts with an emotion tag (`agent/emotion.py` `split_emotion`): the chat shows clean text and the pet plays that mood for 5 s.
- **UI** (`src/ui/`, `src/user_settings.py`) — themed menus (right-click: Chat / Idle↔Wander / Hide Pet), tray icon rendered from `FlameCharacter` (menu: Settings, Quit App, Show Pet only while hidden), Settings window (Language, Outfit Normal/Xmas, Chat AI + one `ApiKeyPanel` per key, Start with Windows, fps 30/60, version in the footer). Settings only emit signals; main applies and saves them; unset values fall back to `config.yaml`.
- **Agent** (`src/agent/`) — `graph.py` `run_agent(history, message)`: LangGraph tool-calling loop over the chosen provider (`set_provider`). Tools in `agent/tools/`: `weather` (Open-Meteo, no key), `web_search` (Tavily), `system_status` (psutil), and the reminder tools `set_timer_reminder` / `list_reminders` / `cancel_reminder` / `dismiss_reminder_bubble`. Gotchas: `resolve_due` computes reminder times in code — never let the model do clock arithmetic; the prompt (`reminder_rules()`) must make the tool call come before any "done" (flash-lite otherwise claims success without calling it — re-check with `src/reminder_check.py` after prompt edits); no/vague time → ask back with a suggestion from `reminders.suggested_times`. Tools catch their own network/API errors and return text so one failure never aborts a turn. Worker failures become in-character English messages via `agent/errors.py` (`friendly_error`), traceback logged.
- **Background monitor** (`src/monitor/background_monitor.py`) — QTimers that poll psutil, fire reminders and emit `ambient_due` every `ambient.interval_minutes` since the last line/click/chat. Reminders live in `monitor/reminders.py` `ReminderStore` (`%LOCALAPPDATA%\Lavenzure\reminders.json`; ones missed while closed fire on startup). The agent tools run on the worker thread, so they only emit queued signals; reminder state stays on the UI thread and other threads read the immutable `pending_reminders()` snapshot. Alerts and reminders share one sticky bubble (`LavenzureApp._show_sticky`) that stays until the user clicks the pet (`_on_pet_clicked` clears both).
- **User activity** (`src/monitor/user_activity.py`) — polls `GetLastInputInfo` and the clock: dozing after `behavior.doze_after_minutes` without input, night look between `behavior.night_start_hour` and `night_end_hour` (night never forces sleep).
- **Pet lines** (`src/pet_lines.py` `PetLines`) — `data/care_lines.json` and `data/facts_jokes.json` (per language, shuffled decks so lines don't repeat until a deck is used up); `random_line` serves the click "speak" reaction, `phrase()` holds alert/reminder texts. Ambient lines are skipped while the pet is hidden or asleep, the chat is open, or a sticky bubble is up.

## Conventions

- Every file starts with a module docstring; every class and function gets a docstring.
- Per-frame code (`face.py`, flame renderers, `FlameCharacter.update/paint`) must keep rendering bit-identical when refactored; verify with the skill's `snap_frames.py`. Physics must not depend on frame rate (`update` sub-steps long frames).
- Prove a change by running it as the user would (real app or `character_preview.py`) and looking at a render; for animation, compare with the reference image before reporting.
