import os
import subprocess
import time
from pathlib import Path

LOG = Path(r"E:\Mecora\backend\_restart_8080.log")
PY = r"E:\Mecora\.venv\Scripts\python.exe"
BACKEND = r"E:\Mecora\backend"

env = dict(os.environ)
# Force the store EXPLICITLY to sqlite so no psycopg import is ever attempted
# (the flapping pid on 8080 was two interpreters fighting; sqlite removes the
# postgres/psycopg dependency entirely and is exactly what the tests use).
env["MECHORA_STORE"] = "sqlite"
env["STORE"] = "sqlite"
env["MECHORA_SQLITE_FALLBACK_PATH"] = r"E:\Mecora\data\mechora_dev.db"
env["SQLITE_FALLBACK_PATH"] = r"E:\Mecora\data\mechora_dev.db"

# Kill whatever currently holds 8080 (both python hearts, force).
killed = []
for tcp in _tcp_8080():
    p = tcp.OwningProcess
    try:
        subprocess.run(
            ["taskkill", "/PID", str(p), "/F", "/T"],
            capture_output=True, timeout=20,
        )
        killed.append(p)
    except Exception as exc:
        print("kill fail", p, exc)

time.sleep(2)

with open(LOG, "w", encoding="utf-8") as fh:
    proc = subprocess.Popen(
        [
            PY,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8080",
        ],
        cwd=BACKEND,
        env=env,
        stdout=fh,
        stderr=subprocess.STDOUT,
        creationflags=(
            getattr(subprocess, "DETACHED_PROCESS", 0)
            | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
            | getattr(subprocess, "CREATE_NO_WINDOW", 0)
        ),
    )
print("relaunched new uvicorn (detached): new_pid =", proc.pid)

# wait + verify the STORE line actually says SQLite (not a crash)
deadline = time.time() + 25
line = None
while time.time() < deadline:
    time.sleep(1)
    if LOG.exists():
        txt = LOG.read_text(encoding="utf-8", errors="replace")
        for ln in txt.splitlines():
            if "MECHORA store" in ln:
                line = ln.strip()
        if "Application startup failed" in txt or "Traceback" in txt:
            print("STARTUP ERROR (see log):")
            sys_stop = max(0, txt.rfind("Traceback"))
            print(txt[sys_stop:][:900])
            raise SystemExit(3)

print("store line :", line)
