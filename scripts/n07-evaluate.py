#!/usr/bin/env python3
"""N07 evaluator: send each case to a real TCP server and compare the reply
with the expected bytes. Writes a JSON verdict file and a CSV next to it."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import platform
import socket
import subprocess
import sys
import time
from datetime import datetime, timezone

VERDICTS = ("pass", "fail", "error")
MAX_RESPONSE = 4096
CASE_KEYS = {"id", "description", "send", "send_hex", "expect", "expect_hex",
             "half_close", "timeout_s", "chunk_delay_ms"}
DEFAULT_KEYS = {"timeout_s", "chunk_delay_ms"}
CSV_FIELDS = ["case_id", "verdict", "expected_text", "actual_text", "expected_hex",
              "actual_hex", "first_diff_offset", "server_closed", "error", "elapsed_ms",
              "description"]


def now():
    return datetime.now(timezone.utc).isoformat()


def sha256(filename):
    with open(filename, "rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def show(data):
    """Printable form of bytes: PONG\\n, \\x00 ..."""
    return data.decode("latin-1").encode("unicode_escape").decode("ascii")


def first_diff(expected, actual):
    for index, (left, right) in enumerate(zip(expected, actual)):
        if left != right:
            return index
    return None if len(expected) == len(actual) else min(len(expected), len(actual))


def number(value, name, minimum, inclusive=True):
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < minimum or (not inclusive and value == minimum)):
        relation = ">=" if inclusive else ">"
        raise ValueError(f"{name} must be a finite number {relation} {minimum}")
    return float(value)


def load_cases(path):
    """Validate a case file and return (meta, cases) with bytes fields resolved."""
    document = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("cases"), list):
        raise ValueError("Case file must be an object with a 'cases' list")
    defaults = document.get("defaults", {})
    if not isinstance(defaults, dict) or set(defaults) - DEFAULT_KEYS:
        raise ValueError(f"'defaults' must be an object with keys from {sorted(DEFAULT_KEYS)}")
    timeout_default = number(defaults.get("timeout_s", 3), "defaults.timeout_s", minimum=0, inclusive=False)
    delay_default = number(defaults.get("chunk_delay_ms", 20), "defaults.chunk_delay_ms", minimum=0)
    seen = set()
    cases = []
    for index, raw in enumerate(document["cases"], 1):
        if not isinstance(raw, dict):
            raise ValueError(f"Case #{index} must be an object")
        case_id = raw.get("id")
        if not isinstance(case_id, str) or not case_id:
            raise ValueError(f"Case #{index} needs a non-empty string 'id'")
        if case_id in seen:
            raise ValueError(f"Duplicate case id: {case_id}")
        seen.add(case_id)
        unknown = set(raw) - CASE_KEYS
        if unknown:
            raise ValueError(f"{case_id}: unknown keys {sorted(unknown)}")
        if ("send" in raw) == ("send_hex" in raw):
            raise ValueError(f"{case_id}: give exactly one of 'send' or 'send_hex'")
        if ("expect" in raw) == ("expect_hex" in raw):
            raise ValueError(f"{case_id}: give exactly one of 'expect' or 'expect_hex'")
        pieces = raw.get("send", raw.get("send_hex"))
        expect = raw.get("expect", raw.get("expect_hex"))
        if (not isinstance(pieces, list) or not all(isinstance(piece, str) for piece in pieces)
                or not isinstance(expect, str)):
            raise ValueError(f"{case_id}: send/send_hex must be a list of strings, expect/expect_hex a string")
        try:
            if "send" in raw:
                chunks = [piece.encode("utf-8") for piece in pieces]
            else:
                chunks = [bytes.fromhex(piece) for piece in pieces]
            expect = expect.encode("utf-8") if "expect" in raw else bytes.fromhex(expect)
        except ValueError as error:
            raise ValueError(f"{case_id}: invalid hex ({error})") from None
        if not chunks or not all(chunks):
            raise ValueError(f"{case_id}: send needs one or more non-empty chunks")
        half_close = raw.get("half_close", False)
        if not isinstance(half_close, bool):
            raise ValueError(f"{case_id}: half_close must be true or false")
        cases.append({
            "id": case_id,
            "description": str(raw.get("description", "")),
            "chunks": chunks,
            "expect": expect,
            "half_close": half_close,
            "timeout_s": number(raw.get("timeout_s", timeout_default), f"{case_id}.timeout_s",
                                minimum=0, inclusive=False),
            "chunk_delay_ms": number(raw.get("chunk_delay_ms", delay_default),
                                     f"{case_id}.chunk_delay_ms", minimum=0),
        })
    meta = {key: document.get(key) for key in ("name", "description", "spec_source")}
    return meta, cases


def exchange(host, port, case):
    """Run one case. The reply ends when the server closes the connection.
    timeout_s bounds the whole case after connecting, not each recv."""
    outcome = {"server_closed": False, "error": None}
    response = bytearray()
    started = time.monotonic()
    try:
        try:
            connection = socket.create_connection((host, port), timeout=case["timeout_s"])
        except socket.timeout:
            outcome["error"] = {"type": "connect_timeout",
                                "message": f"No connection within {case['timeout_s']} s"}
            connection = None
        if connection is not None:
            deadline = time.monotonic() + case["timeout_s"]
            with connection:
                connection.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                connection.settimeout(case["timeout_s"])
                for index, chunk in enumerate(case["chunks"]):
                    if index:
                        time.sleep(case["chunk_delay_ms"] / 1000)
                    connection.sendall(chunk)
                if case["half_close"]:
                    connection.shutdown(socket.SHUT_WR)
                while True:
                    remaining = deadline - time.monotonic()
                    if remaining <= 0:
                        raise socket.timeout()
                    connection.settimeout(remaining)
                    chunk = connection.recv(1024)
                    if not chunk:
                        outcome["server_closed"] = True
                        break
                    response.extend(chunk)
                    if len(response) > MAX_RESPONSE:
                        outcome["error"] = {"type": "response_too_large",
                                            "message": f"Reply exceeded {MAX_RESPONSE} bytes"}
                        break
    except socket.timeout:
        outcome["error"] = {"type": "timeout",
                            "message": f"No server close within {case['timeout_s']} s"}
    except OSError as error:
        outcome["error"] = {"type": type(error).__name__, "message": str(error)}
    outcome["actual"] = bytes(response)
    outcome["elapsed_ms"] = round((time.monotonic() - started) * 1000, 1)
    return outcome


def judge(case, outcome):
    expected, actual = case["expect"], outcome["actual"]
    if outcome["error"]:
        verdict = "error"
    else:
        verdict = "pass" if actual == expected else "fail"
    return {
        "case_id": case["id"],
        "description": case["description"],
        "verdict": verdict,
        "request_chunks_hex": [chunk.hex() for chunk in case["chunks"]],
        "half_close": case["half_close"],
        "expected_hex": expected.hex(),
        "actual_hex": actual.hex(),
        "expected_text": show(expected),
        "actual_text": show(actual),
        "first_diff_offset": first_diff(expected, actual),
        "server_closed": outcome["server_closed"],
        "error": outcome["error"],
        "elapsed_ms": outcome["elapsed_ms"],
    }


def run_cases(host, port, cases):
    return [judge(case, exchange(host, port, case)) for case in cases]


def summarize(results):
    counts = {verdict: sum(1 for item in results if item["verdict"] == verdict)
              for verdict in VERDICTS}
    total = len(results)
    return {"total": total, **counts,
            "pass_rate": round(counts["pass"] / total, 4) if total else None,
            "all_pass": total > 0 and counts["pass"] == total}


def start_server(command, port, log, wait_s=5):
    """Start the server child and wait until it accepts a connection."""
    process = subprocess.Popen(command, stdout=log, stderr=log)
    deadline = time.monotonic() + wait_s
    try:
        while True:
            if process.poll() is not None:
                raise RuntimeError(f"Server exited before listening (code {process.returncode})")
            try:
                socket.create_connection(("127.0.0.1", port), timeout=1).close()
                return process
            except (ConnectionRefusedError, socket.timeout):
                if time.monotonic() > deadline:
                    raise TimeoutError(f"Server did not listen within {wait_s} seconds")
                time.sleep(0.02)
    except BaseException:
        # Never leave the child running when startup fails for any reason.
        stop_server(process)
        raise


def stop_server(process):
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    return process.poll() is not None


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def git_state():
    root = Path(__file__).resolve().parent.parent
    try:
        commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"],
                                         text=True, stderr=subprocess.DEVNULL).strip()
        dirty = bool(subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"],
                                             text=True, stderr=subprocess.DEVNULL).strip())
        return commit, dirty
    except (OSError, subprocess.CalledProcessError):
        return None, None


def write_csv(path, results):
    with open(path, "x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for item in results:
            row = dict(item)
            row["error"] = item["error"]["type"] if item["error"] else ""
            row["first_diff_offset"] = "" if item["first_diff_offset"] is None else item["first_diff_offset"]
            writer.writerow(row)


def parse_args(argv):
    parser = argparse.ArgumentParser(description="N07 expected-vs-actual TCP response evaluator")
    parser.add_argument("--cases", required=True, help="case JSON file")
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--binary", help="server binary; started on a free loopback port and stopped afterwards")
    target.add_argument("--target", help="already running server as HOST:PORT")
    parser.add_argument("--out", required=True, help="new result JSON path; CSV is written next to it")
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    out = Path(args.out).resolve()
    if out.suffix.lower() != ".json":
        raise SystemExit("--out must end in .json (the CSV is written next to it)")
    out.parent.mkdir(parents=True, exist_ok=True)
    csv_path = out.with_suffix(".csv")
    # Refuse to overwrite earlier evidence.
    if csv_path.exists():
        raise FileExistsError(f"Refusing to overwrite {csv_path}")
    with out.open("x", encoding="utf-8"):
        pass
    commit, dirty = git_state()
    result = {"task": "N07", "classification": "practice evaluation (known public spec)",
              "experiment_score": False, "started_at": now(), "stage": "cases",
              "success": False, "argv": [sys.argv[0], *(sys.argv[1:] if argv is None else argv)],
              "python": platform.python_version(), "platform": platform.platform(),
              "code_commit": commit, "code_dirty": dirty}
    process = None
    try:
        cases_path = Path(args.cases).resolve(strict=True)
        meta, cases = load_cases(cases_path)
        result["cases_file"] = {"path": str(cases_path), "sha256": sha256(cases_path), **meta}
        if args.binary:
            binary = Path(args.binary).resolve(strict=True)
            result["input"] = {"path": str(binary), "sha256": sha256(binary)}
            host, port = "127.0.0.1", free_port()
            result["stage"] = "server_start"
            result["server_command"] = [str(binary), str(port)]
            log = (out.parent / (out.name + ".server.stderr")).open("x")
            with log:
                process = start_server(result["server_command"], port, log)
                result["stage"] = "evaluate"
                results = run_cases(host, port, cases)
                # A crash under some input is a finding, not a harness failure: keep the results.
                result["server_exit_code_during_eval"] = process.poll()
            if sha256(binary) != result["input"]["sha256"]:
                raise RuntimeError("Server binary changed during evaluation")
        else:
            host, _, port_text = args.target.rpartition(":")
            if not host or not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
                raise ValueError("--target must be HOST:PORT with port 1-65535")
            port = int(port_text)
            result["stage"] = "evaluate"
            results = run_cases(host, port, cases)
        result["target"] = {"host": host, "port": port}
        result["summary"] = summarize(results)
        result["results"] = results
        write_csv(csv_path, results)
        result["csv"] = str(csv_path)
        result.update(stage="complete", success=True)
    except Exception as error:
        result["error"] = {"type": type(error).__name__, "message": str(error)}
    finally:
        if process is not None:
            result["server_stopped"] = stop_server(process)
        result["finished_at"] = now()
        out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = result.get("summary", {})
    for item in result.get("results", []):
        detail = item["error"]["type"] if item["error"] else f"got \"{item['actual_text']}\""
        print(f"{item['verdict'].upper():5} {item['case_id']:28} expected \"{item['expected_text']}\", {detail}")
    if result.get("server_exit_code_during_eval") is not None:
        print(f"WARNING server exited during evaluation (code {result['server_exit_code_during_eval']})")
    print(json.dumps({"task": "N07", "success": result["success"], "stage": result["stage"],
                      "summary": summary, "result": str(out)}, ensure_ascii=False))
    return 0 if result["success"] and summary.get("all_pass") else 1


if __name__ == "__main__":
    sys.exit(main())
