# N09 실제 모델 호출과 토큰 측정

담당 정의종 · 2026-11-17 · [PR #11](https://github.com/jeonguijong67-hub/byte-by-byte-protocol-agent/pull/11).
PR #10의 A/B prepare 결과에 이어 실제 모델 응답을 받는 실행기다.
**기본 dry-run은 요청을 보내지 않는다.** live는 명시적으로 선택하고 계정의 API 권한·할당량을 확인한 뒤 실행한다.

## 2026-11-25 모델 선택

사용자가 수업에서 모델을 자유롭게 선택할 수 있다고 전달했다.
E1 1차와 공개 연습에 사용한 `gemini-3.5-flash-lite`를 2차에도 사용한다. 11월 25일 계정의 모델 메타데이터 조회에서 버전 `3.5-flash-lite-07-2026`을 확인했다.

Copilot Pro+ 활성화는 GitHub 메일로 확인했다. Copilot SDK로 구독을 연결할 경우 [SDK 인증 설정](https://docs.github.com/en/copilot/how-tos/copilot-sdk/auth)을 사용한다. 현재 N09는 Gemini의 Chat Completions 호환 엔드포인트와 Gemini API 키를 사용한다.

11월 25일 Codex가 코드 `77d113e`로 공개 N06을 조건별 한 번 실행했다. 양쪽 요청·응답 모델 ID가 일치했고, A 3,772토큰, B 10,097토큰을 기록했다. A는 정상 응답에 가변 오류 코드와 배열을 포함해 참조 브리지에서 `spec_unexecutable`로 기록했다. B는 공개 정상 프레임 통신 15/15를 통과했다. 실행 원본은 로컬 `runs/gemini/2026-11-25T04-18-45-693Z/`에 있다.

11월 25일 공개 N10으로 E1 요청을 A/B 각 5회 오프라인 점검했다. 이 점검에서 10개 고유 분석 ID와 공통 프롬프트 해시 및 모델 설정을 확인했다. 해당 오프라인 점검의 API 호출은 0회다.

## 11월 24일 E1 1차 본 실험

실행 코드 `3f2dc5b30c8f0fbb63a6a666eea90726eebc6168`, 모델 `gemini-3.5-flash-lite`, 공통 프롬프트 SHA-256 `57c0c94824ccbf0249c6b2cea32bc6a29860b3d100236d46a757f3fc04d26b27`.
실제 API 요청 10회와 N11 v1 채점을 완료했다. 채점 담당자가 전한 주 항목 15개 기준 결과다.

| 조건 | API 시도 | HTTP 503 | 응답 형식 검증 실패 | 검증된 후보 | N11 v1 점수 합계 |
| --- | ---: | ---: | ---: | ---: | ---: |
| A | 5 | 2 | 1 | 2 | 1/75 |
| B | 5 | 3 | 0 | 2 | 0/75 |

핸드오프 결과 10개의 SHA-256과 저장된 요청 본문 10개의 기록 해시를 대조했다. B의 5개 요청에는 같은 `binary-1` 번들이 들어갔다. 번들은 Ghidra 개요와 함수 검색 결과로 구성됐고 선택 함수·디컴파일 결과는 0건이었다. 정상 응답을 받은 B3·B5의 관찰 4건은 모두 패킷을 인용했다. 검증된 후보 4개는 첫 요청·응답 헤더만 다뤘다. 1차는 최초 본 실험 기록으로 보존하며, 프롬프트가 변경된 2차는 자체 결과를 보고한다.

## E1 2차 시행 규칙 · 2026-11-26

- **비교 조건** A는 `tcp-streams-v1` 패킷 근거, B는 같은 패킷 근거와 기존 `named-procedure-v1` 번들이다. 이 N10에서는 B가 바이너리 개요와 함수 검색 결과까지 제공한다. 쌍 요약에는 `packet_format`과 `rea_detail_profile.selected_procedure`가 남는다.
- **공통 설정** Gemini Chat Completions 호환 API의 `gemini-3.5-flash-lite`, `max_tokens=4096`, JSON 모드 on, 시간 제한 120초, 시행당 호출 1회, N11 v1 주 항목 15개. Gemini 3.5 Flash-Lite의 API에서 샘플링 매개변수가 사용 중단됐으므로 요청에서 온도를 생략하고 두 조건에 제공자 기본 동작을 적용한다. 결과의 `model.temperature: null`은 매개변수 생략을 나타낸다. [Google의 API 변경 안내](https://ai.google.dev/gemini-api/docs/gemini-3#sampling-parameter-deprecation)
- **실행 전 기록** 깨끗한 체크아웃으로 A/B를 다시 준비하고 쌍 검사에 통과한 결과를 보관한다. 실행 커밋, N10 PCAP·바이너리 해시, 공통 프롬프트 SHA-256 `ae0efeb6ae678581cccef76d1db33f49fc925439718e7c0a78af0b5866f743ae`, 설정과 요청 파일 해시를 확인한다. 응답에 모델 ID가 있으면 각 회차의 `model.returned`를 대조하고, 값이 없거나 예상 ID와 다르면 그 사실을 기록한다.
- **순서와 상한** A와 B의 시도를 번갈아 진행해 조건별 채점 대상 5회를 확보한다. 조건별 API 시도는 최대 10회다. 조건 하나가 채점 대상 5회에 도달하면 다른 조건의 남은 회차를 진행한다. 상한에서 5회를 확보하지 못한 조건은 미완료로 보고한다.
- **제공사·전송 오류** HTTP 429·5xx 또는 `MODEL_TIMEOUT`은 API 시도 횟수에 넣고 원본 오류와 시각을 보존한다. 채점 대상 회차는 유지하고 다음 조건의 차례를 진행한 뒤, 해당 조건 차례에 같은 준비 입력과 `repeat`로 새 `analysis_run_id`를 만든다. `Retry-After`가 있으면 같은 조건의 재호출에 적용한다. 인증·요청 설정 오류 등 그 밖의 실행 오류가 나면 기록을 남기고 중단한다.
- **모델 응답 실패** HTTP 2xx 응답을 모두 읽은 뒤 `candidate_validation`에서 발생한 오류는 채점 대상 회차의 실패로 기록하고 다음 회차로 진행한다. 여기에는 `API_JSON`, `API_CHOICES`, `OUTPUT_TRUNCATED`, `MODEL_NO_ANSWER`, `EMPTY_CANDIDATE`, `CANDIDATE_JSON`, `UNEXPECTED_TOOL_CALL`, `OUTPUT_SCHEMA`, `QUOTE_MISMATCH`가 포함된다. 결과 JSON과 원본 응답을 보관한다.
- **2차 결과 집계** 점수와 함께 조건별 API 시도 수, 채점 대상 회차 수, HTTP 503 건수, `MODEL_TIMEOUT` 건수, 기타 제공사 오류 건수를 각각 기록한다.

## 2026-11-17 계정·크레딧 조사 기록

- 세종 멀티LLM은 학생 월3,000크레딧, 매월1일 초기화로 안내한다. 이 값은 API 토큰 수가 아니다.
- 공개 공지에서 외부 프로그램용 API 제공·키 발급·모델별 차감률은 확인하지 못했다. 연결된 메일에서도 관련 안내를 찾지 못했다.
- 현재 실행 환경에 LLM_API_KEY/OPENAI_API_KEY/GEMINI_API_KEY 등 사용 가능한 API 설정은 발견되지 않았다.
- 학교 포털의 API/개발자 설정과 차감표는 로그인한 사용자가 확인해야 한다. 웹 채팅 크레딧을 OpenAI/Gemini API 키 대신 넣을 수는 없다.
- 일부 ChatGPT Pro/Business 구독의 API 크레딧 혜택은 조건·활성화가 필요하다. 실제 계정의 지급 여부는 확인하지 않았다.
- 새 계정 생성·과금 결제·API 크레딧 활성화·실제 유료 모델 요청은 수행하지 않았다.

공식 안내:
- [고려대 세종 멀티LLM 공지](https://korstudy.korea.ac.kr/bbs/kucec/132/273083/artclView.do)
- [OpenAI 구독/API 크레딧 혜택](https://help.openai.com/en/articles/20001626-api-credits-benefit-for-eligible-chatgpt-subscriptions)
- [Gemini API 요금·무료 티어](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini OpenAI 호환 API](https://aistudio.google.com/docs/openai)
- [Chat Completions 규격](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)

## 준비 결과부터 만들기

[기존 N09 실행법](n09-ab-preparation.md)으로 공개 N06 연습 자료의 A/B 결과를 만든다.
준비 JSON과 원본 증거·선택 PCAP/바이너리가 같은 파일 경로에서 읽혀야 한다.
Docker에서 만든 /work 경로를 호스트 Windows 경로로 바꾸지 않는다. 이어지는 명령도 같은 N05 컨테이너 환경을 쓴다.

키 없이 점검:

```powershell
docker compose -f compose.n05.yaml run --rm n05 node scripts/n09-live.mjs --prepared "runs/n09/A-준비태그.json" --out "runs/n09-live/A-audit-새태그.json"
```

기대: success true, model_called false, usage.api_requests 0.
설정이 없으면 configuration.missing에 필요한 변수 이름만 남긴다.
기존 결과는 덮어쓰지 않는다.

## 실제 모델 호출

필수 변수:
- LLM_CHAT_COMPLETIONS_URL: 전체 HTTPS Chat Completions 주소
- LLM_MODEL: 계정에서 실제 사용할 수 있는 정확한 모델 ID
- LLM_API_KEY: 로컬 환경변수의 키

선택 변수:
- LLM_MAX_TOKENS_PARAM: 기본 max_completion_tokens. 제공사가 max_tokens를 요구하면 명시적으로 변경
- LLM_JSON_MODE: 기본 off, 제공사가 지원하는 경우 on으로 json_object 요청
- LLM_TEMPERATURE: 기본 미지정. 지원 확인 후 지정하며 A/B 양쪽 동일하게 유지

사용 예시의 모델 ID는 계정에서 선택해야 한다. 웹사이트의 표시명과 API ID가 같다고 가정하지 않는다.
기존 N05 compose는 필수3개 변수를 전달한다. 선택 변수는 -e로 전달한다.

```powershell
$env:LLM_CHAT_COMPLETIONS_URL = 'https://제공사가-안내한-주소/v1/chat/completions'
$env:LLM_MODEL = '계정에서-확인한-정확한-모델-ID'
$llmSecureKey = Read-Host 'API key' -AsSecureString
$env:LLM_API_KEY = [System.Net.NetworkCredential]::new('', $llmSecureKey).Password
$env:LLM_MAX_TOKENS_PARAM = 'max_completion_tokens'
$env:LLM_JSON_MODE = 'off'
$runTag = Get-Date -Format 'yyyyMMdd-HHmmss'
docker compose -f compose.n05.yaml run --rm -e LLM_MAX_TOKENS_PARAM -e LLM_JSON_MODE n05 node scripts/n09-live.mjs --prepared "runs/n09/A-준비태그.json" --out "runs/n09-live/A-$runTag.json" --execution live
docker compose -f compose.n05.yaml run --rm -e LLM_MAX_TOKENS_PARAM -e LLM_JSON_MODE n05 node scripts/n09-live.mjs --prepared "runs/n09/B-준비태그.json" --out "runs/n09-live/B-$runTag.json" --execution live
```

공식 호환 주소의 예시는 다음과 같다. 사용 가능 모델/요금/무료 할당량은 계정에서 별도 확인한다.

| 서비스 | 전체 요청 주소 |
| --- | --- |
| OpenAI API | https://api.openai.com/v1/chat/completions |
| Gemini OpenAI 호환 API | https://generativelanguage.googleapis.com/v1beta/openai/chat/completions |
| 학교 API | 실제 제공 여부·주소 미확인. 학교 웹 채팅 URL을 요청 주소로 사용하지 않음 |

## 결과·사용량을 읽는 법

- run_id와 analysis_run_id: 이번 모델 실행의 동일한 고유 ID. CSV/체크리스트가 이 ID를 계승하거나 매핑한다.
- preparation_run_id: 원래 입력 준비 실행의 ID. 같은 준비 입력을 재사용해도 모델 실행 ID는 매번 새로 만든다.
- model.requested/returned: 요청한 ID와 API가 반환한 모델 식별자. operator_confirmed는 자동으로 true로 바꾸지 않는다.
- model.temperature에는 요청에 지정한 온도를 기록한다. 제공자 기본값을 쓰면 null로 남긴다. 이 실행기는 seed를 보내지 않는다. response_id와 시작·종료 시각으로 응답을 추적한다.
- usage.api_requests: 실제 요청 시도 횟수. HTTP429/실패도 1회로 기록하며 자동 재시도하지 않는다.
- usage.prompt_tokens/completion_tokens/total_tokens: API가 보고한 값. 누락되면 null이고 임의 추정치를 채우지 않는다.
- usage.provider: 캐시·추론 토큰 등을 포함한 원본 usage 구조. 학교 크레딧으로 자동 환산하지 않는다.
- artifacts: 요청 JSON, 원본 API 응답, SHA-256과 단계별 성공/실패. API 키는 저장 내용에서 치환한다.
- runtime.source_fingerprint: 실제 실행 코드 파일들의 SHA-256. 새 준비 결과에 코드 해시가 있으면 호출 전에 현재 코드와 대조한다. 다르면 SOURCE_CHANGED로 요청 없이 중단하고 새 prepare 실행이 필요하다.
- spec/observations/unknowns: 후보 결과. 형식과 실제 근거 인용의 일치를 검증한다. 의미상 정답 여부는 N11에서 평가한다.

실행기가 보존하는 결과는 후보 명세다. experiment_score, n05_complete, n09_complete는 false다.
N12가 요구하는 실행 가능 명세의 스키마는 별도 합의해야 한다. 빈 spec·빈 관찰·없는 인용문·잘린 응답은 실패로 보존한다.

## 호출·토큰 예산

현재 실행기는 한 시행당 **1회만** API를 호출하며 그 상한을 runtime.max_model_calls에 기록한다. 기존 공통 예산의 최대2호출보다 작은 범위다.
출력 상한4096, 시간 제한120초, 서버 질의0회, 자동 재시도0회다.
제공사에 따라 추론 토큰이 출력 한도를 공유할 수 있으므로, 실제 응답의 usage/finish_reason으로 확인한다.

- A/B 각5회: 현재 실행기로 총10개 API 요청. 출력 한도 합계는40,960토큰이다.
- 입력 토큰 수는 제공사 토크나이저에 따라 다르다. 최초 공개 연습 A/B 각1회에서 실제 usage를 측정한다.
- 학교 차감 예산은 같은 모델/입력 설정으로 관찰한 A/B 차감액을 바탕으로 잡는다. 3,000크레딧을 3,000토큰으로 계산하지 않는다.
- 준비 상태에서 말한 전체100만~200만토큰은 개발·재실행 여유를 포함한 추정이었다. 실제 호출 로그가 생기면 다시 계산한다.
- 무료 API의 분당토큰/일일요청 한도가 입력보다 작으면 요청이 거부될 수 있다. 429는 보존하고 다음 실행 시점을 정한다.
- 본 실험에는 모델·프롬프트·입력 버전·출력 상한·온도·평가 기준을 먼저 고정하고, 중간에 다른 모델 결과를 섞지 않는다.

## N05/N12·블라인드 조건

N09-live는 선택한 근거를 미리 준비해 모델에게 주는 경로다. 모델이 요청한 임의 도구는 실행하지 않는다.
실제 모델의 도구 호출→REA→동일 호출ID→요약은 기존 N05 full 명령으로 별도 검증해야 한다.
현재 binary_overview만으로 모든 프로토콜을 복원할 수 있다고 보장하지 않는다. 함수 검색/디컴파일이 필요하면 별도 도구·예산 버전으로 구현한다.

최초 pilot은 공개 N06 연습 입력을 사용한다. 본 실험 N10의 숨은 정답·소스·평가 입력은 분석 환경에 넣지 않는다.
새 모델에 맞춘 연결 점검은 연습 자료로 끝내고 본 실험 프롬프트·평가 기준을 고정한다.

## 테스트와 남은 확인

```powershell
node --test scripts/rea-smoke.test.mjs scripts/n09-contract.test.mjs scripts/n09-prepare.test.mjs scripts/n09-live.test.mjs scripts/n09-check-pair.test.mjs
```

기존55개+신규19개, 합계74개. 실제 루프백 HTTP fixture를 포함한다.
이 fixture는 실제 LLM이 아니며 model_called false와 injected-api-protocol-test로 표시한다.

2026-11-17 로컬 연습 재실행 보완: 기존74개에 코드 변경 감지1개와 쌍 검증 회귀8개를 더해
현재 총83개다. 쌍 검증 기본값은 clean checkout을 요구하며 로컬 공개 연습에서만
`--allow-dirty`로 실제 소스 해시를 대조하며 실행할 수 있다. CI 기본값은 유지한다.

리뷰 대상: 권세현(A/B 조건·토큰/실패·실행ID), 유현석(후보 명세·N12 호환).
남은 확인: 계정 API 사용 가능 여부, 실제 모델·URL·한도, 연습 A/B 각1회 실제 호출과 usage/명세 의미 검토.
