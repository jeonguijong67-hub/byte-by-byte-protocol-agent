# N05 public practice TCP fixture

This team-owned fixture is only for wiring N05 to a real binary and real TCP
response. Its public source and known protocol are allowed during practice.
It is separate from the hidden source, reference specification and evaluation
inputs of the real experiment. Practice results are not experiment scores.
Replace this input with N06's practice binary when it is available.

## Build on Linux / WSL

Requirements: GCC, Python 3 and a Linux shell. From the repository root:

```sh
mkdir -p /work/runs/n05
gcc -O0 -fno-inline -o /work/runs/n05/practice-server practice/n05/ping-server.c
sha256sum /work/runs/n05/practice-server
```

The unstripped build retains function names and the strings `PING`, `PONG` and
`ERR`, making REA evidence straightforward to inspect. Record the actual binary
SHA-256 for every run; compiler/toolchain changes can change it. Build outputs
and raw execution evidence belong under the Git-ignored `runs/` directory.

## Exchange one command

In one terminal, start the service in the foreground:

```sh
/work/runs/n05/practice-server 19005
```

In another terminal in the same Linux environment:

```sh
python3 - <<'PY'
import socket
with socket.create_connection(("127.0.0.1", 19005), timeout=3) as connection:
    connection.sendall(b"PING\n")
    response = bytearray()
    while True:
        chunk = connection.recv(64)
        if not chunk:
            break
        response.extend(chunk)
    print(repr(bytes(response)))
PY
```

Expected output: `b'PONG\n'`. Stop the foreground service with Ctrl+C after the
exchange. If started in the background, retain its PID (`server_pid=$!` directly
after starting it) and stop that exact process with `kill "$server_pid"` then
`wait "$server_pid"` when finished. Do not leave practice servers running.

The optional first argument selects a port from 1 to 65535; the default is
19005. The service binds only to loopback. It handles one newline-terminated
request per connection and then closes the connection. It accumulates up to
63 request bytes across `recv` calls. The exact bytes `PING\n` produce
`PONG\n`; other complete or overlong requests produce `ERR\n`. An early EOF
produces no response. This deliberately small sequential service is for a
controlled local smoke run; it has no concurrent-client or load-test behavior.

Use the binary path and its SHA-256 with the instructions in
[`docs/rea-smoke.md`](../../docs/rea-smoke.md) to run the LLM/REA stage. A
successful known-protocol socket exchange alone does not complete N05: the
real course model must request the tool, receive real REA evidence, summarize
it, and have a claim checked against the original evidence.
