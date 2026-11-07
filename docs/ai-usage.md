# AI 사용 기록

`내가 직접 확인한 것`은 각 행 작성자 본인의 검토 내역이다. AI/자동 테스트 결과를 본인 확인으로 대신 적지 않는다. 확인 후 해당 칸을 갱신한다.

| 날짜 (KST) | 작성자 | 작업 번호 | 사용 도구 | AI에 맡긴 일 | 내가 직접 확인한 것 |
| --- | --- | --- | --- | --- | --- |
| 2026-11-05 | 정의종 | N05 | Codex, 보조 에이전트, REA/Ghidra, Docker, Node 테스트 | 도구 호출 스크립트·공개 연습 TCP fixture·설치/실행법 작성, 오류 경로와 실제 REA/소켓 검증, 증거·PR 초안 작성 | 확인 필요: 코드/실행 JSON 원본, REA 근거와 주장 의미, 수업 모델 ID 및 실제 전체 연동. 실제 수행 결과는 docs/evidence/N05-2026-11-05.md 참조 |
| 2026-11-07 | 권세현 | N07 | Claude Code, 보조 리뷰 에이전트, Docker, WSL | 평가기 `scripts/n07-evaluate.py`·모의 테스트·케이스 파일(정상/틀린 명세)·실행법 작성, 리뷰 지적 반영, Docker/WSL 실제 연습 서버 실행 | WSL에서 직접 실행(2026-11-07 KST): ① 모의 테스트 19개 OK. ② `--binary`로 정상 명세 10/10 pass·exit 0, 틀린 명세 pass 1/fail 4/error 1·exit 1, CSV에서 `missing-newline-in-reply`의 `first_diff_offset` 4 확인(기대 `504f4e47`, 실제 `504f4e470a`). ③ 평가기 없이 bash `/dev/tcp`로 `HELLO\n` 전송 → `ERR` 수신, 평가기의 `wrong-command-name` 실제값 `ERR\n`과 일치. 직접 띄운 서버에 `--target`으로 10/10 pass. 같은 결과 경로로 다시 실행하면 덮어쓰지 않고 거부함을 확인. ④ 케이스 복사본에서 `ping-crlf` 기대값을 `OK\n`으로 바꾸자 그 케이스만 fail(실제 `ERR\n`), 9 pass·exit 1. ⑤ 평가 후 `pgrep -fa practice-server` 결과 없음. 바이너리 SHA-256 `545ef393…`(N05 기록과 동일). 원본: 로컬 `runs/n07/my-*` |
