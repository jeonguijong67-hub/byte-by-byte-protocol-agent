# N05: REA smoke run

작업 번호 **N05**, 담당 **정의종**. 입력은 운영자가 선택한 팀 소유 연습 바이너리와 새 결과 JSON 경로다. 이번 주(2026-11-04~11-08) 내부 목표는 한 TCP 명령의 분석 단계와 실제 서버 응답을 준비하는 것이다. N06 자료가 도착하면 바이너리만 교체한다.

## 완료 기준과 현재 한계

수업 모델의 실제 `tool_calls` → 실제 REA/Ghidra → 같은 `tool_call_id`로 근거 반환 → 모델 요약 → JSON 저장 → 요약의 주장 하나를 원본에서 확인해야 N05 완료다. `success: true`는 해당 모드의 실행 성공이다. `n05_complete`는 자동으로 true가 되지 않으며, 수업 모델 ID 확인과 주장 의미의 본인 검토는 `확인 필요`로 남는다. 따옴표 일치만으로 주장의 의미까지 검증되지는 않는다.

- **모의 검증**: `--mock` 또는 단위 테스트. 외부 API/REA를 사용하지 않는다.
- **실제 REA 단독**: `--rea-only`. 실제 doctor/analyze를 실행한다. 모델 호출은 없다.
- **실제 전체 연동**: 옵션 없는 실행. 설정 누락/도구 요청 누락/API/REA 오류는 실패로 보관한다. 시도 기록의 분류가 전체 연동이라고 해서 성공한 것은 아니다.
- **연습 TCP 교환**: 알려진 `PING\n`을 보내 `PONG\n`을 확인하는 별도 검증이다. 분석에서 명령을 복원했다는 증거와 본 실험 점수에 포함하지 않는다.

수업 공개 [9주차](https://2026-lecture-network.vercel.app/js/weeks/w09.js)와 [10주차](https://2026-lecture-network.vercel.app/js/weeks/w10.js)는 Upstage Solar 사용을 안내한다. 세부 모델 ID와 계정 API 키는 제공되지 않았다. 2026-11-05 담당자는 다음 주에 키를 받을 예정이라고 확인했다. 전체 연동을 완료로 표시하지 않는다. 실행 결과는 [공유용 증거](evidence/N05-2026-11-05.md)에 별도로 기록한다.

## 설치 조건

호스트: Git, Docker Desktop의 Linux 엔진. 모의 테스트만 실행할 때는 Node 22 이상으로 충분하다. 실제 REA 6.8.0에는 Node `^22.23.4 || ^24.22.1 || >=26.12.1`이 필요하다. 이번 Docker 환경은 Ubuntu24.04, Node24.22.1, REA6.8.0, Ghidra12.1.4, full JDK21, procps, GCC, Python3을 사용한다. Ghidra ZIP은 공식 SHA-256으로 검증하고 Node 배포본은 공식 SHASUMS와 비교한다. Linux x86-64용 구성이다.

설치는 [REA 공식 문서](https://github.com/morluto/rea/blob/main/docs/installation.md), 명령은 [CLI 문서](https://github.com/morluto/rea/blob/main/docs/cli.md), Ghidra 체크섬은 [공식 릴리스](https://github.com/NationalSecurityAgency/ghidra/releases/tag/Ghidra_12.1.4_build)를 따른다. 최초 이미지 다운로드에는 수백 MB와 수 분이 필요하다. apt 패키지는 빌드 시점 버전이므로 실행 JSON/공유 증거에 실제 버전을 남긴다.

PowerShell에서 저장소 루트로 이동한 뒤:

```powershell
New-Item -ItemType Directory -Force runs/n05 | Out-Null
docker compose -f compose.n05.yaml build n05
docker compose -f compose.n05.yaml run --rm n05 gcc -O0 -fno-inline -Wall -Wextra -o runs/n05/practice-server practice/n05/ping-server.c
$runTag = Get-Date -Format 'yyyyMMdd-HHmmss'
```

컨테이너에는 저장소를 읽기 전용으로 연결하고 `runs/`만 쓰기 허용한다. 숨긴 소스/정답/평가 입력은 이 저장소와 컨테이너 마운트 밖에 둔다. 이미지 빌드 문맥은 `infra/n05/`뿐이다. 호스트의 다른 앱/MCP 설정은 변경하지 않는다.

## 키 없이 지금 실행

```powershell
node --test scripts/rea-smoke.test.mjs
docker compose -f compose.n05.yaml run --rm n05 node scripts/rea-smoke.mjs --mock runs/n05/practice-server "runs/n05/mock-$runTag.json"
docker compose -f compose.n05.yaml run --rm n05 node scripts/rea-smoke.mjs --rea-only runs/n05/practice-server "runs/n05/rea-$runTag.json"
docker compose -f compose.n05.yaml run --rm n05 python3 scripts/n05-practice-exchange.py runs/n05/practice-server "runs/n05/tcp-$runTag.json"
```

단독 REA 실행은 내부에서 다음 명령을 수행하고 stdout/stderr를 보관한다.

```sh
rea --version
rea doctor --provider ghidra --json
rea analyze /work/runs/n05/practice-server --provider ghidra --json
```

모의/REA 단독은 `stage: complete`, `success: true`가 기대 결과다. TCP 결과는 `response_hex: 504f4e470a`, `response_text: "PONG\n"`, `server_stopped: true`가 기대 결과다. TCP 검증은 서버를 자식 프로세스로 띄우고 종료하며 외부 포트를 공개하지 않는다. 실행 중 포트 충돌이면 새 결과 경로로 재실행한다.

`analyze`의 현재 기능은 `binary_overview`다. 함수/문자열 개수와 분석 범위/한계를 관찰할 수 있지만 문자열 내용이나 의사코드가 반드시 제공되지는 않는다. 개요만으로 PING/PONG 프로토콜을 복원했다고 주장하지 않는다. 이후 N06/N08의 복원 작업에 더 자세한 REA 조회가 필요할 수 있다.

## 다음 주 실제 모델 연동

API 키는 채팅/명령 인자/문서에 쓰지 않는다. 저장소 `.env`도 만들 필요 없다. 수업 계정에서 실제 모델 ID와 URL을 확인한 다음 같은 PowerShell 창에서 설정한다. 아래 URL은 [Upstage 공식 API](https://console.upstage.ai/api/chat)의 공개 주소이며 계정/수업 설정이 다르면 확인된 주소를 사용한다.

```powershell
$env:LLM_CHAT_COMPLETIONS_URL = 'https://api.upstage.ai/v1/chat/completions'
$env:LLM_MODEL = '<수업 계정에서 확인한 실제 모델 ID>'
$solarSecret = Read-Host 'Solar API key' -AsSecureString
$env:LLM_API_KEY = [System.Net.NetworkCredential]::new('', $solarSecret).Password
$runTag = Get-Date -Format 'yyyyMMdd-HHmmss'
docker compose -f compose.n05.yaml run --rm n05 node scripts/rea-smoke.mjs runs/n05/practice-server "runs/n05/full-$runTag.json"
Remove-Item Env:LLM_API_KEY
```

키가 없으면 `configuration / MISSING_CONFIGURATION` 실패를 저장하고 외부 요청은 보내지 않는다. 매 실행 새 경로를 사용한다. 기존 결과/입력은 덮어쓰지 않는다. HTTP 오류, 도구 호출 누락, REA 오류도 삭제하지 않고 보관한다. 실패하면 해당 단계의 원인을 해결하고 새 경로로 위 명령을 다시 실행한다.

일반 Linux/WSL에 이미 도구가 있다면 아래와 같이 사용할 수 있다.

```sh
export GHIDRA_INSTALL_DIR=/absolute/ghidra_12.1.4_PUBLIC
# rea-agents@6.8.0, full JDK21, procps 및 지원 Node 필요
node scripts/rea-smoke.mjs --rea-only /absolute/practice-binary runs/n05/rea-new.json
# LLM_CHAT_COMPLETIONS_URL / LLM_MODEL / LLM_API_KEY 설정 후:
node scripts/rea-smoke.mjs /absolute/practice-binary runs/n05/full-new.json
```

## 실행 JSON과 원본 대조

JSON은 실행 시각(UTC ISO8601), N05/모드, 코드 커밋과 dirty 여부, 명령 인자, 입력 경로/크기/SHA-256, Node/REA 버전과 doctor, 요청/응답 모델 ID, 단계별 상태, 도구 호출 ID, REA 근거와 원본 위치, 최종 요약, 검증 결과, 실패 코드/단계를 담는다. 로컬 JSON의 시각은 KST로 +9시간 하여 주간 기록에 넣는다. 결과 파일 옆의 고유 `.artifacts-*` 폴더에 API 요청 본문/응답과 REA stdout/stderr를 저장한다. 키와 Authorization 헤더는 기록하지 않으며 알려진 API 키는 저장 내용에서 가린다. REA 자식 환경에는 LLM/키/토큰 환경변수를 전달하지 않는다.

모델에는 REA 원본 첫 **24KiB 이내** UTF-8 발췌문과 원본 SHA-256/바이트 범위를 전달한다. 원본은 로컬에 보관한다. API 응답은 2MiB/120초 제한, REA 명령은 10분 제한/원본 64MiB까지 파싱한다. 제한 초과/강제 종료는 성공으로 처리하지 않는다. REA 원본은 디스크로 저장하고 분석 바이너리를 실행하지 않는다. 모델이 파일/명령을 고르지 못하도록 인자 없는 도구 하나만 제공하며 `{}`가 아닌 인자, 알 수 없는 도구와 복수 호출은 거부한다.

전체 연동 성공 뒤 같은 실행 JSON에서 다음을 대조한다.

1. `model.requested`/`returned`가 수업 지정 계정의 모델인지 직접 확인한다.
2. `tool_call.id`와 `evidence.tool_call_id`, 두 번째 API 요청의 tool 메시지 `tool_call_id`가 같은지 확인한다.
3. `summary.claims` 중 하나를 `verification.matches`의 원본 파일/바이트 범위에서 찾고 SHA-256을 대조한다. 인용문이 실제 주장을 뒷받침하는지 직접 읽는다.
4. `verification.all_quotes_match: true`와 위 수동 확인을 별도 로컬 리뷰 기록에 작성하고 `docs/ai-usage.md`의 본인 확인란을 갱신한다. 확인 전에는 완료 표시하지 않는다.

종료 코드 0은 해당 모드 성공, 1은 실패, 사용법 오류는 2다. REA 개요의 분석 한계도 보존한다. 외부 API 오류 응답에는 민감 정보가 있을 수 있으므로 원자료는 공유 전에 별도로 검토한다.

## 공유와 기여 기록

원본 JSON, 바이너리, API 응답/로그, 설치 산출물은 Git에서 제외한 `runs/`에 보관한다. `.artifacts-*`도 제외한다. `runs/` 밖에 결과를 지정할 경우 운영자가 별도로 Git 제외와 보관을 책임진다. 공개 가능한 결과 요약만 `docs/evidence/`에 기록하고 PR에서 링크한다. 키/비공개 정답/숨은 평가 입력은 공유하지 않는다.

각 작업은 작업 번호로 코드·문서·실행 증거·리뷰를 연결한다. PR에는 작업 번호/변경 내용/재실행 명령/실제 결과와 증거/남은 검증/리뷰 포인트를 넣는다. `docs/ai-usage.md`에는 날짜/작성자/작업 번호/사용 도구/AI에 맡긴 일/직접 확인을 추가한다. 이후 그래프에는 원본 CSV, 조건, 실행 스크립트, 그래프 생성 명령을 연결한다.

발표에서 설명할 핵심: 도구 실행 파일은 모델이 아니라 운영자가 고른다. 모의 검증과 실제 모델 연동을 구분한다. 근거 인용의 문자열 일치와 주장의 의미 확인은 다르다. 패킷만 본 조건과 바이너리 근거를 더한 조건의 모델/예산을 맞춘다.
