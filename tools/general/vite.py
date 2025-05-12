import subprocess
import time
import sys
import re
from typing import Tuple
from .subprocess import get_env

def wait_for_vite_port(proc, timeout=20):
    port = None
    start = time.time()
    while time.time() - start < timeout:
        line = proc.stdout.readline()
        if not line:
            time.sleep(0.1)
            continue
        try:
            text = line.decode(sys.stdout.encoding or 'utf-8', errors='replace')
        except Exception:
            text = line.decode('utf-8', errors='replace')
        print(text, end='')
        match = re.search(r"localhost:(\d+)", line.decode(errors="ignore"))
        if match:
            port = int(match.group(1))
            print(f"[manage.py] Detected Vite dev server at http://localhost:{port}")
            return port
    print("Could not detect Vite dev server port from output.")
    exit(1)

def forward_streams(proc):
    import threading
    def forward(src, dst):
        while True:
            data = src.readline()
            if not data:
                break
            try:
                text = data.decode(dst.encoding or 'utf-8', errors='replace')
            except Exception:
                text = data.decode('utf-8', errors='replace')
            print(text, end='', file=dst)
    threads = []
    if proc.stdout:
        t = threading.Thread(target=forward, args=(proc.stdout, sys.stdout), daemon=True)
        t.start()
        threads.append(t)
    if proc.stderr:
        t = threading.Thread(target=forward, args=(proc.stderr, sys.stderr), daemon=True)
        t.start()
        threads.append(t)
    return threads

def start_vite() -> Tuple[int, subprocess.Popen]:
    vite_proc = subprocess.Popen(["pnpm", "run", "dev"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=get_env())
    port = None
    print(f"Started Vite dev (PID {vite_proc.pid})")
    try:
        port = wait_for_vite_port(vite_proc)
        if not port:
            print("Could not detect Vite dev server port from output.")
            vite_proc.terminate()
            sys.exit(1)
        print(f"Vite dev server is running at http://localhost:{port}")
        # Forward all further output
        forward_streams(vite_proc)
    except Exception as e:
        print(f"Error starting Vite dev server: {e}")
        vite_proc.terminate()
        sys.exit(1)
    return port, vite_proc