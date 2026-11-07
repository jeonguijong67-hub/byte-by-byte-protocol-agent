# N07: 기대 응답 vs 실제 응답 자동 평가기

작업 번호 **N07**, 담당 **권세현**. 케이스 파일의 요청을 실제 TCP 서버에 보내고, 받은 응답 바이트를 기대 바이트와 비교해 판정 JSON과 CSV를 남긴다. 이번 주 입력은 N05의 공개 연습 서버(`practice/n05/ping-server.c`)다. 공개 소스와 알려진 프로토콜로 만든 기대값이므로 **연습 결과는 본 실험 점수가 아니다**(`experiment_score: false`).

## 구성

| 파일 | 역할 |
| --- | --- |
| `scripts/n07-evaluate.py` | 평가기. Python 3.11+ 표준 라이브러리만 사용 |
| `scripts/test_n07_evaluate.py` | 모의 테스트 19개. C 서버 대신 같은 동작의 Python 서버를 사용 |
| `practice/n07/cases.json` | 연습 서버의 실제 명세(README)대로 쓴 기대값 10개 — 모두 `pass`가 기대 결과 |
| `practice/n07/cases-mismatch.json` | 일부러 틀린 명세(음성 대조군) 6개 — 대조군 1개만 `pass`, 나머지는 `fail`/`error`가 기대 결과 |

## 판정 규칙

- 연결 → 요청 조각을 순서대로 전송(조각 사이 `chunk_delay_ms`, TCP_NODELAY) → `half_close`면 쓰기 방향 종료 → **서버가 연결을 닫을 때까지** 수신한다. 연습 서버는 응답 후 연결을 닫는다.
- `pass`: 서버가 닫았고 받은 바이트 전체가 기대 바이트와 정확히 같다. 앞부분만 같고 뒤에 더 붙으면 `fail`이다.
- `fail`: 정상적으로 받았지만 바이트가 다르다. `first_diff_offset`에 처음 다른 위치를 기록한다.
- `error`: 연결 실패(`connect_timeout` 포함), 연결 후 `timeout_s` 안에 서버가 닫지 않음(`timeout`, 수신마다가 아니라 케이스 전체 시간), 연결 리셋, 응답 4096바이트 초과. 원인은 `error.type`에 남는다.
- 케이스 형식: `send`(UTF-8 문자열 조각 목록) 또는 `send_hex`, `expect`(문자열) 또는 `expect_hex`, 선택 `description`/`half_close`(true/false)/`timeout_s`(>0)/`chunk_delay_ms`(>=0). `defaults`에는 `timeout_s`, `chunk_delay_ms`만 둔다. id 중복, 빈 조각, 둘 다/둘 다 없음, 잘못된 타입·범위, 모르는 키(오타)는 서버 연결 전에 거부하고 `stage: cases`로 기록한다.
- 종료 코드: 모든 케이스 `pass`면 0, 하나라도 `fail`/`error`이거나 실행이 중단되면 1, 명령 인자 오류는 2. 불일치 대조군 실행은 **종료 코드 1이 정상**이며, 이때도 `success: true`(평가 자체는 끝까지 수행)다.

## 출력

`--out runs/n07/<이름>.json`과 같은 위치에 `<이름>.csv`, 바이너리 모드라면 `<이름>.json.server.stderr`를 만든다. 기존 파일은 덮어쓰지 않는다. JSON에는 시작/종료 시각, 코드 커밋과 dirty 여부, Python/플랫폼, 케이스 파일 SHA-256, 서버 바이너리 SHA-256, 서버 명령과 종료 확인(`server_stopped`, 평가 도중 서버가 죽었으면 `server_exit_code_during_eval`에 종료 코드), 요약(`total/pass/fail/error/pass_rate/all_pass`), 케이스별 요청 hex·기대/실제 hex·텍스트·차이 위치·소요 시간을 기록한다. CSV는 케이스당 한 줄이다. 원본 결과는 Git에서 제외되는 `runs/`에 둔다.

## 실행

### 모의 테스트 (컴파일러 불필요, Windows/Linux)

```powershell
python -m unittest discover -s scripts -p "test_n07*.py" -v
```

### 실제 연습 서버 — Docker (N05와 같은 이미지)

PowerShell, 저장소 루트. N05 실행법대로 이미지를 빌드한 뒤:

```powershell
New-Item -ItemType Directory -Force runs/n07 | Out-Null
docker compose -f compose.n05.yaml run --rm n05 gcc -O0 -fno-inline -Wall -Wextra -o runs/n07/practice-server practice/n05/ping-server.c
$runTag = Get-Date -Format 'yyyyMMdd-HHmmss'
docker compose -f compose.n05.yaml run --rm n05 python3 scripts/n07-evaluate.py --cases practice/n07/cases.json --binary runs/n07/practice-server --out "runs/n07/eval-known-$runTag.json"
docker compose -f compose.n05.yaml run --rm n05 python3 scripts/n07-evaluate.py --cases practice/n07/cases-mismatch.json --binary runs/n07/practice-server --out "runs/n07/eval-mismatch-$runTag.json"
```

### 실제 연습 서버 — WSL/Linux

```sh
mkdir -p runs/n07
gcc -O0 -fno-inline -Wall -Wextra -o runs/n07/practice-server practice/n05/ping-server.c
tag=$(date +%Y%m%d-%H%M%S)
python3 scripts/n07-evaluate.py --cases practice/n07/cases.json --binary runs/n07/practice-server --out "runs/n07/eval-known-$tag.json"
python3 scripts/n07-evaluate.py --cases practice/n07/cases-mismatch.json --binary runs/n07/practice-server --out "runs/n07/eval-mismatch-$tag.json"
```

`--binary`는 빈 루프백 포트를 골라 `<바이너리> <포트>`로 서버를 자식 프로세스로 띄우고, 평가 후 종료한다(`server_stopped: true`). 컴파일러 버전이 다르면 바이너리 SHA-256도 달라지므로 실행마다 기록된 값을 사용한다.

### 이미 실행 중인 서버 (N08 웹·다른 바이너리 연결용)

```sh
python3 scripts/n07-evaluate.py --cases practice/n07/cases.json --target 127.0.0.1:19005 --out runs/n07/eval-target-$tag.json
```

이 모드는 서버를 띄우거나 끄지 않고 바이너리 해시도 기록하지 않으므로, 어떤 서버였는지 별도로 기록한다.

## 기대 결과

- `cases.json`: `summary` = `total 10, pass 10, fail 0, error 0`, 종료 코드 0.
- `cases-mismatch.json`: `total 6, pass 1, fail 4, error 1`. `missing-newline-in-reply`는 `first_diff_offset: 4`(기대 `PONG`, 실제 `PONG\n`), `no-terminator-assumption`은 개행 없는 요청에 서버가 계속 기다리므로 `error.type: timeout`. 종료 코드 1.

## 한계와 다음 단계

- 연습 서버는 한 줄만 읽고 연결을 닫으므로, 개행 **뒤에** 바이트를 더 보내는 케이스는 서버 쪽에 읽지 않은 데이터가 남아 연결 리셋(RST)이 나고, 응답을 받았더라도 `error`가 될 수 있다(타이밍 의존). 그런 케이스는 이 서버에 넣지 않는다.
- 응답의 끝을 "서버가 연결을 닫음"으로 판단한다. 한 연결에서 여러 메시지를 주고받는 본 실험 프로토콜에는 길이/구분자 기준 수신과 세션형 케이스가 추가로 필요하다.
- 기대값은 사람이 연습 서버 README로 작성했다. 본 실험에서는 **추론 명세에서 만든 기대값**을 케이스 파일로 넣어, 실제 서버 응답과의 일치율을 복원 정확도 지표로 쓴다. 정답 명세·숨은 평가 입력은 이 저장소 밖에 둔다.
- N06 연습 바이너리가 오면 `--binary`만 바꾸고 그 명세로 케이스 파일을 새로 만든다.
- 순차 처리 연습 서버이므로 동시 접속·부하 측정은 하지 않는다.
