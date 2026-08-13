"""On-demand system status tool (separate from the proactive BackgroundMonitor alerts)."""
from __future__ import annotations

import psutil
from langchain_core.tools import tool


@tool
def system_status() -> str:
    """Report the current CPU usage, RAM usage, and battery level of the user's PC."""
    cpu = psutil.cpu_percent(interval=0.3)
    ram = psutil.virtual_memory().percent
    battery = psutil.sensors_battery()
    battery_text = f"{battery.percent:.0f}%" if battery else "no battery detected"
    return f"CPU: {cpu:.0f}%, RAM: {ram:.0f}%, Battery: {battery_text}."
