# byte-by-byte-protocol-agent
LLM- and REA-assisted reconstruction of custom TCP protocols, with compatible clients and reproducible network experiments.

- [Gemini N05/N09 pilot and N12 wire-spec handoff](docs/n09-wire-handoff.md)

## Reproduce and contribute

- [N05 REA smoke runner](docs/rea-smoke.md)
- [N05 observed results (2026-11-05)](docs/evidence/N05-2026-11-05.md)
- [N07 expected-vs-actual response evaluator](docs/n07-evaluator.md)
- [N02/N06 practice SUM protocol, capture and cases](practice/n06/README.md)
- [N06 observed results (2026-11-08)](docs/evidence/N06-2026-11-08.md)
- [N10 experiment analysis inputs](experiment/n10/README.md)
- [Task, evidence and contribution rules](CONTRIBUTING.md)
- [N05–N07 integration handoff](docs/integration-handoff.md)
- [Windows Docker integration evidence (2026-11-09)](docs/evidence/N05-N07-integration-2026-11-09.md)
- [N03 evaluation sheet and result CSV format](docs/n03-evaluation-format.md)


## A/B 준비와 진행 보고

- [N09 실행법](docs/n09-ab-preparation.md) · [2026-11-13 실행 증거](docs/evidence/N09-2026-11-13.md)
- [11/9~11/15 진행 기록·개인별 다음 작업](docs/weekly/2026-11-09-to-11-15.md)
- [LMS Week 10 영문 초안](docs/weekly/week10-progress-report.md)

2026-11-17 공개 Gemini 연습에서 최종 A/B 후보로 정상 TCP 프레임 통신을 각각 15/15 확인했다. [실행 기록](docs/evidence/N05-N09-Gemini-integration-2026-11-17.md).

11월 24일 본 실험 E1 1차의 N11 v1 채점 합계는 A 1/75, B 0/75다. API 503 5회와 응답 형식 검증 실패 1회가 포함됐고, 채점 결과가 A/B 우열을 판단하기에는 제한적이다. 11월 25일 공개 연습 재검증에서는 A가 `spec_unexecutable`였고 B의 정상 프레임 통신은 15/15였다. N05/N09 전체 검증과 N12 웹 통합은 진행 중이다.

2026-11-25 사용자 전달 기준 수업에서 모델을 자유롭게 선택할 수 있다. E1 2차도 Gemini 3.5 Flash-Lite를 사용하며 [E1 결과와 2차 시행 규칙](docs/n09-live-model.md)을 따른다.
