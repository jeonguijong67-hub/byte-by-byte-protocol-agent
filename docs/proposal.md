# Byte by Byte — Project Proposal

**Title:** REA-Assisted Reconstruction and Validation of a Custom TCP Application Protocol  
**Team:** Byte by Byte  
**Repository:** https://github.com/jeonguijong67-hub/byte-by-byte-protocol-agent  
**Status:** Proposal draft; not a confirmation of LMS submission.

## English submission text

We will use an LLM agent and REA to reconstruct the message formats and interaction rules of a custom TCP application without providing its source code or reference protocol specification during analysis. We will compare packet-only analysis with packet-plus-binary analysis to evaluate how additional binary evidence affects reconstruction accuracy. Based on the inferred specification, we will implement a compatible client and validate it using unseen inputs, fragmented and combined message delivery, and controlled network delay and loss. We will provide a deployed demonstration, reconstruction and communication measurements, raw data, reproducibility scripts, and a statement of each member's contribution.

## 한국어 설명

소스코드와 정답 명세를 분석 단계에서 제공하지 않은 상태에서 LLM 에이전트와 REA로 자체 TCP 프로그램의 메시지 형식과 통신 규칙을 복원한다. 패킷 기록만 제공한 조건과 실행파일 분석 정보를 추가한 조건을 비교하여, 추가 정보가 복원 결과에 미치는 영향을 평가한다. 추론한 명세로 호환 클라이언트를 구현하고 새로운 입력, 메시지 분할·합침, 지연·손실 조건에서 실제 통신을 검증한다. 배포 데모, 측정 원자료, 재현 스크립트와 팀원별 기여도를 제출한다.

## Minimum scope

- One team-owned C TCP test service; start with three commands and add a fourth only if schedule permits.
- The challenge author keeps reference source, specification, answer key and held-out tests outside the analysis workspace and this public repository until the initial evaluation is frozen.
- Any command excluded from the packet captures must still be implemented and reachable in the provided analysis binary.
- Use the course-designated LLM. Current course slides name Upstage Solar, while an earlier LMS notice discussed GLM support; confirm the applicable model and test real tool invocation before building the full pipeline.
- Keep the same model, prompt-development effort and comparable resource limits across conditions; document the information each condition receives.
- Treat the comparison as the effect of adding binary-analysis evidence, not proof of the isolated superiority of a particular tool.

## Evaluation and outputs

1. A predefined checklist of approximately 15 protocol facts, scored with absolute counts and percentages.
2. Correct responses and successful interactions on inputs not used during inference.
3. Parser tests using one-byte, variable-size and concatenated message chunks, plus real socket integration tests.
4. Controlled delay/loss tests reporting correct completion, timeouts and connection failures separately.
5. Request-rate sweeps reporting offered/completed request rates, p50/p95 latency and throughput for valid requests.

Run both analysis conditions five independent times initially, retain every run and record human interventions. This is a small course-project evaluation; conclusions remain limited to the tested program and conditions.

## LMS submission checklist

- Add the final team member names and student IDs in LMS, as required by the assignment; they are not published in this repository.
- Include the project title, the four-sentence explanation and the repository URL.
- Have the team leader submit once and verify the submission receipt/status.
- Update the team sheet with the topic and repository URL.
- Last observed LMS topic deadline: **2026-11-03 23:59 Korea time**; recommended internal submission date: **2026-11-02**.

## References

- [Week 09 Team Building & Project Topic](https://mylms.korea.ac.kr/courses/97879/assignments/266274)
- [Official course slides](https://2026-lecture-network.vercel.app/)
- [REA](https://github.com/morluto/rea)
- [Weekly execution plan](project-plan.md)
