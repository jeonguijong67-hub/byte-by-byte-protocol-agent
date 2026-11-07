"""Mock tests for scripts/n07-evaluate.py. A Python stand-in follows the
documented behaviour of practice/n05/ping-server.c, so no compiler is needed.
Run: python3 -m unittest discover -s scripts -p "test_n07*.py" -v"""
import csv
import importlib.util
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("n07_evaluate", ROOT / "scripts" / "n07-evaluate.py")
n07 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n07)

FAKE_SERVER = r'''
import socket, sys
listener = socket.socket()
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", int(sys.argv[1])))
listener.listen(4)
while True:
    client, _ = listener.accept()
    request = b""
    while len(request) < 63:
        byte = client.recv(1)
        if not byte:
            break
        request += byte
        if byte == b"\n":
            break
    else:
        byte = b"x"
    if byte:
        client.sendall(b"PONG\n" if request == b"PING\n" else b"ERR\n")
    client.close()
'''


class FakePracticeServer:
    """Sequential in-process copy of the practice server for tests."""

    def __init__(self, reply=None):
        self.reply = reply
        self.listener = socket.socket()
        self.listener.bind(("127.0.0.1", 0))
        self.listener.listen(4)
        self.port = self.listener.getsockname()[1]
        self.thread = threading.Thread(target=self.serve, daemon=True)
        self.thread.start()

    def serve(self):
        while True:
            try:
                client, _ = self.listener.accept()
            except OSError:
                return
            with client:
                request, complete = b"", False
                while len(request) < 63:
                    byte = client.recv(1)
                    if not byte:
                        break
                    request += byte
                    if byte == b"\n":
                        complete = True
                        break
                if not complete and len(request) < 63:
                    continue
                if self.reply is not None:
                    client.sendall(self.reply)
                else:
                    client.sendall(b"PONG\n" if request == b"PING\n" else b"ERR\n")

    def close(self):
        self.listener.close()


def case(**overrides):
    base = {"id": "c", "description": "", "chunks": [b"PING\n"], "expect": b"PONG\n",
            "half_close": False, "timeout_s": 2, "chunk_delay_ms": 0}
    base.update(overrides)
    return base


class LoadCasesTest(unittest.TestCase):
    def write(self, document):
        handle = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
        with handle:
            json.dump(document, handle)
        self.addCleanup(Path(handle.name).unlink)
        return handle.name

    def test_repository_case_files_load(self):
        _, good = n07.load_cases(ROOT / "practice" / "n07" / "cases.json")
        _, wrong = n07.load_cases(ROOT / "practice" / "n07" / "cases-mismatch.json")
        self.assertEqual(len(good), 10)
        self.assertEqual(len(wrong), 6)
        overlong = next(item for item in good if item["id"] == "overlong-63-bytes")
        self.assertEqual(len(overlong["chunks"][0]), 63)

    def test_hex_and_defaults(self):
        path = self.write({"defaults": {"timeout_s": 7}, "cases": [
            {"id": "h", "send_hex": ["00ff", "0a"], "expect_hex": "4552520a"}]})
        _, cases = n07.load_cases(path)
        self.assertEqual(cases[0]["chunks"], [b"\x00\xff", b"\n"])
        self.assertEqual(cases[0]["expect"], b"ERR\n")
        self.assertEqual(cases[0]["timeout_s"], 7)

    def test_rejects_bad_files(self):
        bad = [
            {"cases": [{"send": ["x"], "expect": ""}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": ""}, {"id": "a", "send": ["x"], "expect": ""}]},
            {"cases": [{"id": "a", "send": ["x"], "send_hex": ["00"], "expect": ""}]},
            {"cases": [{"id": "a", "send": ["x"]}]},
            {"cases": [{"id": "a", "send_hex": ["zz"], "expect": ""}]},
            {"cases": [{"id": "a", "send": [], "expect": ""}]},
            {"cases": [{"id": "a", "send": [""], "expect": ""}]},
            {"no_cases": []},
            {"cases": [{"id": "a", "send": "PING\n", "expect": ""}]},
            {"cases": [{"id": "a", "send": [1], "expect": ""}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": 5}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "half_close": "false"}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "half-close": True}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "timeout_s": 0}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "timeout_s": -1}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "timeout_s": "3"}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "timeout_s": True}]},
            {"cases": [{"id": "a", "send": ["x"], "expect": "", "chunk_delay_ms": -5}]},
            {"defaults": {"timeout_s": 1e999}, "cases": [{"id": "a", "send": ["x"], "expect": ""}]},
            {"defaults": {"timeout": 3}, "cases": [{"id": "a", "send": ["x"], "expect": ""}]},
            {"defaults": [], "cases": [{"id": "a", "send": ["x"], "expect": ""}]},
            {"cases": ["not-an-object"]},
        ]
        for document in bad:
            with self.subTest(document=document):
                with self.assertRaises(ValueError):
                    n07.load_cases(self.write(document))


class CompareTest(unittest.TestCase):
    def test_first_diff(self):
        self.assertIsNone(n07.first_diff(b"PONG\n", b"PONG\n"))
        self.assertEqual(n07.first_diff(b"PONG\n", b"ERR\n"), 0)
        self.assertEqual(n07.first_diff(b"PONG", b"PONG\n"), 4)
        self.assertEqual(n07.first_diff(b"", b"ERR\n"), 0)

    def test_show_escapes(self):
        self.assertEqual(n07.show(b"PONG\n"), "PONG\\n")
        self.assertEqual(n07.show(b"\x00\xff"), "\\x00\\xff")

    def test_summary(self):
        results = [{"verdict": "pass"}, {"verdict": "fail"}, {"verdict": "error"}, {"verdict": "pass"}]
        self.assertEqual(n07.summarize(results), {"total": 4, "pass": 2, "fail": 1, "error": 1,
                                                  "pass_rate": 0.5, "all_pass": False})
        self.assertFalse(n07.summarize([])["all_pass"])


class ExchangeTest(unittest.TestCase):
    def setUp(self):
        self.server = FakePracticeServer()
        self.addCleanup(self.server.close)

    def test_known_spec_all_pass(self):
        _, cases = n07.load_cases(ROOT / "practice" / "n07" / "cases.json")
        results = n07.run_cases("127.0.0.1", self.server.port, cases)
        self.assertEqual([item["verdict"] for item in results], ["pass"] * len(cases),
                         [(item["case_id"], item["actual_text"], item["error"]) for item in results])
        eof = next(item for item in results if item["case_id"] == "eof-before-newline")
        self.assertEqual(eof["actual_hex"], "")
        self.assertTrue(eof["server_closed"])

    def test_wrong_spec_detected(self):
        _, cases = n07.load_cases(ROOT / "practice" / "n07" / "cases-mismatch.json")
        results = {item["case_id"]: item for item in n07.run_cases("127.0.0.1", self.server.port, cases)}
        self.assertEqual(results["control-ping"]["verdict"], "pass")
        for case_id in ("missing-newline-in-reply", "wrong-command-name",
                        "case-insensitive-assumption", "crlf-assumption"):
            self.assertEqual(results[case_id]["verdict"], "fail", case_id)
        self.assertEqual(results["missing-newline-in-reply"]["first_diff_offset"], 4)
        self.assertEqual(results["wrong-command-name"]["actual_text"], "ERR\\n")
        timeout = results["no-terminator-assumption"]
        self.assertEqual(timeout["verdict"], "error")
        self.assertEqual(timeout["error"]["type"], "timeout")
        self.assertFalse(timeout["server_closed"])

    def test_extra_bytes_fail(self):
        extra = FakePracticeServer(reply=b"PONG\nEXTRA")
        self.addCleanup(extra.close)
        result = n07.judge(case(), n07.exchange("127.0.0.1", extra.port, case()))
        self.assertEqual(result["verdict"], "fail")
        self.assertEqual(result["first_diff_offset"], 5)

    def test_oversized_reply_is_error(self):
        big = FakePracticeServer(reply=b"A" * (n07.MAX_RESPONSE + 10))
        self.addCleanup(big.close)
        result = n07.judge(case(), n07.exchange("127.0.0.1", big.port, case()))
        self.assertEqual(result["verdict"], "error")
        self.assertEqual(result["error"]["type"], "response_too_large")

    def test_timeout_bounds_whole_case(self):
        listener = socket.socket()
        listener.bind(("127.0.0.1", 0))
        listener.listen(1)
        self.addCleanup(listener.close)

        def drip():
            client, _ = listener.accept()
            with client:
                try:
                    for _ in range(30):
                        client.sendall(b"A")
                        time.sleep(0.1)
                except OSError:
                    pass

        threading.Thread(target=drip, daemon=True).start()
        slow = case(timeout_s=0.5)
        outcome = n07.exchange("127.0.0.1", listener.getsockname()[1], slow)
        self.assertEqual(outcome["error"]["type"], "timeout")
        self.assertLess(outcome["elapsed_ms"], 1500)
        self.assertTrue(outcome["actual"].startswith(b"A"))

    def test_connection_refused_is_error(self):
        result = n07.judge(case(), n07.exchange("127.0.0.1", n07.free_port(), case()))
        self.assertEqual(result["verdict"], "error")
        self.assertIsNotNone(result["error"])


class ServerProcessTest(unittest.TestCase):
    def test_start_evaluate_stop(self):
        port = n07.free_port()
        with tempfile.TemporaryFile() as log:
            process = n07.start_server([sys.executable, "-c", FAKE_SERVER, str(port)], port, log)
            try:
                result = n07.judge(case(), n07.exchange("127.0.0.1", port, case()))
            finally:
                self.assertTrue(n07.stop_server(process))
        self.assertEqual(result["verdict"], "pass")

    def test_server_that_exits_is_reported(self):
        with tempfile.TemporaryFile() as log:
            with self.assertRaises(RuntimeError):
                n07.start_server([sys.executable, "-c", "raise SystemExit(3)"], n07.free_port(), log)


class MainTest(unittest.TestCase):
    def setUp(self):
        self.server = FakePracticeServer()
        self.addCleanup(self.server.close)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)

    def run_main(self, cases_name, out_name):
        out = Path(self.directory.name) / out_name
        code = n07.main(["--cases", str(ROOT / "practice" / "n07" / cases_name),
                         "--target", f"127.0.0.1:{self.server.port}", "--out", str(out)])
        return code, out

    def test_writes_json_and_csv(self):
        code, out = self.run_main("cases.json", "good.json")
        self.assertEqual(code, 0)
        record = json.loads(out.read_text(encoding="utf-8"))
        self.assertEqual(record["task"], "N07")
        self.assertTrue(record["success"])
        self.assertFalse(record["experiment_score"])
        self.assertEqual(record["summary"]["pass"], 10)
        self.assertEqual(len(record["cases_file"]["sha256"]), 64)
        with out.with_suffix(".csv").open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        self.assertEqual([row["verdict"] for row in rows], ["pass"] * 10)
        self.assertEqual(list(rows[0]), n07.CSV_FIELDS)

    def test_mismatch_run_exits_nonzero_but_completes(self):
        code, out = self.run_main("cases-mismatch.json", "wrong.json")
        self.assertEqual(code, 1)
        record = json.loads(out.read_text(encoding="utf-8"))
        self.assertTrue(record["success"])
        self.assertEqual(record["summary"], {"total": 6, "pass": 1, "fail": 4, "error": 1,
                                             "pass_rate": 0.1667, "all_pass": False})
        with out.with_suffix(".csv").open(encoding="utf-8", newline="") as stream:
            errors = {row["case_id"]: row["error"] for row in csv.DictReader(stream)}
        self.assertEqual(errors["no-terminator-assumption"], "timeout")

    def test_refuses_overwrite(self):
        self.run_main("cases.json", "same.json")
        with self.assertRaises(FileExistsError):
            self.run_main("cases.json", "same.json")

    def test_out_must_be_json(self):
        with self.assertRaises(SystemExit):
            self.run_main("cases.json", "result.csv")

    def test_bad_target_recorded(self):
        out = Path(self.directory.name) / "bad.json"
        code = n07.main(["--cases", str(ROOT / "practice" / "n07" / "cases.json"),
                         "--target", "no-port", "--out", str(out)])
        self.assertEqual(code, 1)
        record = json.loads(out.read_text(encoding="utf-8"))
        self.assertFalse(record["success"])
        self.assertEqual(record["error"]["type"], "ValueError")


if __name__ == "__main__":
    unittest.main()
