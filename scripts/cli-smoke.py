#!/usr/bin/env python3
"""Exercise the packaged server, HTTP listener and real pairing command."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

binary = sys.argv[1]
subprocess.run([binary, "--version"], check=True)
with tempfile.TemporaryDirectory(prefix="t3-cli-smoke-") as temporary:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
    base = Path(temporary)
    environment = os.environ.copy()
    environment["HOME"] = str(base)
    with (base / "server.log").open("w+") as log:
        server = subprocess.Popen([binary, "serve", "--base-dir", str(base / "state"),
                                   "--host", "127.0.0.1", "--port", str(port)],
                                  env=environment, stdout=log, stderr=log)
        try:
            for _ in range(120):
                if server.poll() is not None:
                    raise RuntimeError("Packaged T3 server exited before HTTP became ready")
                try:
                    with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=1) as response:
                        if response.status == 200:
                            break
                except OSError:
                    pass
                time.sleep(0.25)
            else:
                raise RuntimeError("Packaged T3 server did not become ready")
            pairing = subprocess.run([binary, "pair", "--base-dir", str(base / "state"), "--ttl", "1m"],
                                     env=environment, capture_output=True, text=True, timeout=20)
            if pairing.returncode or "Pairing URL:" not in pairing.stdout + pairing.stderr:
                raise RuntimeError("Packaged T3 pairing command failed")
            print("Packaged server HTTP and pairing passed")
        finally:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
