"""
System tools — time, host info, live machine status, launching applications.
"""

from __future__ import annotations

import datetime
import platform
import shutil
import subprocess
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from salaam.config import config

# Spoken name → what to actually launch. Falls through to the raw name so
# "open spotify" still works even if it isn't listed here.
KNOWN_APPS = {
    "browser": "https://www.google.com",
    "chrome": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "file explorer": "explorer",
    "files": "explorer",
    "terminal": "wt",
    "cmd": "cmd",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "settings": "ms-settings:",
    "spotify": "spotify",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
    "whatsapp": "https://web.whatsapp.com",
    "youtube": "https://www.youtube.com",
    "gmail": "https://mail.google.com",
}


def register(mcp):

    @mcp.tool()
    def get_current_time(timezone: str = "") -> str:
        """
        Current date and time. Defaults to the user's home timezone.

        Args:
            timezone: an IANA name like "Africa/Lagos", "America/New_York" or "UTC".
        """
        name = timezone.strip() or config.TIMEZONE
        try:
            zone = ZoneInfo(name)
        except ZoneInfoNotFoundError:
            # Windows ships no IANA database, so a perfectly valid name fails
            # here unless the `tzdata` package is installed.
            local = datetime.datetime.now().astimezone()
            return (
                f"{local.strftime('%A, %d %B %Y at %I:%M %p')} (local time). "
                f"I couldn't resolve the \"{name}\" timezone — this machine has "
                "no IANA timezone database. Install it with: pip install tzdata"
            )
        except ValueError:
            return f'"{name}" isn\'t a valid timezone name. Try something like "Africa/Lagos".'

        now = datetime.datetime.now(zone)
        return f"{now.strftime('%A, %d %B %Y at %I:%M %p')} ({name})"

    @mcp.tool()
    def get_system_info() -> dict:
        """Basic information about the host machine."""
        return {
            "os": platform.system(),
            "os_version": platform.version(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "python_version": platform.python_version(),
        }

    @mcp.tool()
    def get_system_status() -> str:
        """
        Live machine health — CPU load, memory, disk and battery.
        Use for "how's my system doing?" or "what's my battery at?".
        """
        try:
            import psutil
        except ImportError:
            return (
                "Detailed status needs the psutil package. "
                "Install it with: pip install psutil"
            )

        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        lines = [
            "### System status",
            f"- CPU: {psutil.cpu_percent(interval=0.5)}% across {psutil.cpu_count()} cores",
            f"- Memory: {memory.percent}% used "
            f"({memory.used / 1e9:.1f} GB of {memory.total / 1e9:.1f} GB)",
            f"- Disk: {disk.percent}% used "
            f"({disk.free / 1e9:.1f} GB free of {disk.total / 1e9:.1f} GB)",
        ]

        battery = getattr(psutil, "sensors_battery", lambda: None)()
        if battery is not None:
            state = "charging" if battery.power_plugged else "on battery"
            lines.append(f"- Battery: {battery.percent:.0f}% ({state})")

        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        uptime = datetime.datetime.now() - boot
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        lines.append(f"- Uptime: {hours}h {remainder // 60}m")
        return "\n".join(lines)

    @mcp.tool()
    def open_app(name: str) -> str:
        """
        Launch an application or site on the user's machine — for example
        "notepad", "spotify", "calculator", "vscode", "whatsapp", "youtube".
        """
        key = name.strip().lower()
        target = KNOWN_APPS.get(key, key)

        if target.startswith(("http://", "https://", "ms-settings:")):
            import webbrowser

            webbrowser.open(target)
            return f"Opening {name} now."

        try:
            if platform.system() == "Windows":
                subprocess.Popen(["cmd", "/c", "start", "", target], shell=False)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", "-a", target])
            else:
                if not shutil.which(target):
                    return f'I couldn\'t find an application called "{name}" on this machine.'
                subprocess.Popen([target])
            return f"Launching {name} now."
        except Exception as error:
            return f'I couldn\'t launch "{name}": {error}'
