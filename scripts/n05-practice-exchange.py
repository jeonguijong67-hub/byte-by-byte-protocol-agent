#!/usr/bin/env python3
"""N05 known practice PING exchange; never an inferred-protocol score."""
import hashlib
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(filename):
    with open(filename, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 scripts/n05-practice-exchange.py <practice-binary> <new-result.json>")
        return 2
    target = Path(sys.argv[2]).resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("x", encoding="utf-8"):
        pass
    result = {"task": "N05", "classification": "practice TCP exchange (known input)",
              "started_at": now(), "success": False, "stage": "input",
              "argv": sys.argv, "python": platform.python_version(),
              "n05_complete": False, "inferred_protocol_validation": False}
    process = None
    try:
        binary = Path(sys.argv[1]).resolve(strict=True)
        result["input"] = {"path": str(binary), "sha256": sha256(binary)}
        result["code_commit"] = subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parent.parent), "rev-parse", "HEAD"],
            text=True).strip()
        result["code_dirty"] = bool(subprocess.check_output(
            ["git", "-C", str(Path(__file__).resolve().parent.parent), "status", "--porcelain"], text=True).strip())
        result["gcc"] = subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]
        # Pick an available loopback port, then let the practice child bind it.
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            port = probe.getsockname()[1]
        result["stage"] = "server_start"
        result["server_command"] = [str(binary), str(port)]
        with (target.parent / (target.name + ".server.stderr")).open("x") as log:
            process = subprocess.Popen(result["server_command"], stdout=log, stderr=log)
            deadline = time.monotonic() + 5
            while True:
                if process.poll() is not None:
                    raise RuntimeError("Practice server exited before connection")
                try:
                    connection = socket.create_connection(("127.0.0.1", port), timeout=1)
                    break
                except ConnectionRefusedError:
                    if time.monotonic() > deadline:
                        raise TimeoutError("Practice server did not listen within 5 seconds")
                    time.sleep(0.02)
            result["stage"] = "socket_exchange"
            with connection:
                connection.settimeout(3)
                # Deliberately split the one command across writes.
                for piece in (b"PI", b"NG", b"\n"):
                    connection.sendall(piece)
                response = bytearray()
                while True:
                    chunk = connection.recv(64)
                    if not chunk:
                        break
                    response.extend(chunk)
                    if len(response) > 1024:
                        raise RuntimeError("Practice response exceeded 1024 bytes")
            result["exchange"] = {"request_hex": b"PING\n".hex(),
                "write_chunks_hex": [b"PI".hex(), b"NG".hex(), b"\n".hex()],
                "response_hex": bytes(response).hex(), "response_text": bytes(response).decode("ascii"),
                "expected_hex": b"PONG\n".hex()}
            if bytes(response) != b"PONG\n":
                raise RuntimeError("Unexpected practice response")
            if sha256(binary) != result["input"]["sha256"]:
                raise RuntimeError("Practice binary changed during exchange")
            result.update(success=True, stage="complete")
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
            result["server_stopped"] = process.poll() is not None
        result["finished_at"] = now()
        target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"task": "N05", "success": result["success"], "stage": result["stage"], "result": str(target)}))
    return 0 if result["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
