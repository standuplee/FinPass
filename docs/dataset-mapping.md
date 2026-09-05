# Dataset Inspection & Mapping Plan

## 출처별 역할과 확인 항목

| 데이터셋 | 입력 단위 | FinPass 대상 | Phase 0 확인 항목 |
| --- | --- | --- | --- |
| BPI Challenge 2017 | Case/Event Log | Journey/Event/Step/Duration | Activity, lifecycle, timestamp, case ID, offer/application 관계 |
| Banking77 | `text`, `label`, `label_text` | Intent Taxonomy | Train 10,003건, Test 3,080건, 77개 Label, 한국 금융업무 매핑 가능성 |
| AI-Hub 금융 고객상담 | 대화/발화/메타데이터 | Consultation Case, Intent, RAG Chunk | 화자, 상담분류, 개인정보, 이용조건, 문서 구조 |
| AI-Hub 금융상품·소비자 특성 | 상품/속성/소비자 관계 | Product KB, Retrieval Metadata | 상품 식별자, 조건, 기준시점, 소비자 특성, 라이선스 |

## BPI 2017 초기 매핑

실제 원본 Schema를 검사한 후 확정해야 하며 아래는 개발용 가설이다.

| BPI 개념/Activity | FinPass Event/Step | 처리 |
| --- | --- | --- |
| Application 생성 | `JOURNEY_STARTED` | Case 시작 Event |
| 신청 정보 제출 | Business Information | 유사 Activity 묶음을 단계 완료로 정규화 |
| 검증 Activity | Identity/Income Verification | Activity 속성과 순서로 분기, 직접 동일시 금지 |
| Offer 생성 | `LIMIT_CHECK_COMPLETED` | MVP 한도조회 Proxy로만 활용 |
| 추가정보 요청 | `DOCUMENT_REQUIRED` | 반복·대기 패턴 생성 근거 |
| Application 완료 | `JOURNEY_COMPLETED` | Terminal State 매핑 |

원본 BPI Activity가 FinPass의 모바일 화면 Event와 의미상 완전히 같다고 가정하지 않는다. Process 전이와 시간 분포를 Synthetic 생성에 활용하고, 제품 Event는 별도 Taxonomy를 유지한다.

## Banking77 초기 매핑

| Banking77 Label | 내부 Intent | 비고 |
| --- | --- | --- |
| `verify_source_of_funds` | `VERIFY_SOURCE_OF_FUNDS` | 소득·자금출처 확인 보조 |
| `verify_my_identity` | `UNABLE_TO_VERIFY_IDENTITY` | 실제 Label 존재 여부와 의미 재확인 필요 |
| 미매핑 Label | `UNMAPPED` | 억지 매핑 없이 검토 Queue로 이동 |

Banking77은 영문 소비자 뱅킹 Intent이므로 국내 개인사업자 대출 Taxonomy의 정답 데이터로 직접 사용하지 않는다. 분류 사전학습·Baseline과 용어 확장에만 사용한다.

MVP는 Hugging Face의 `mteb/banking77` 리비전 `18072d2`를 사용한다. 원본 배포본은 MIT 라이선스이며 `train`, `test` 두 Split으로 구성된다. `make banking77`은 각 Split을 Parquet으로 내보내고 실제 Dataset fingerprint와 Label 목록을 `data/processed/intents/banking77/profile.json`에 기록한다.

## 데이터 Provenance Manifest 필수 필드

- Dataset 이름, 버전, 원본 URL 또는 AI-Hub ID
- 다운로드·검사 일시와 담당자
- 라이선스, 보관·재배포·상업적 이용 조건
- 원본 파일 해시와 파일 수
- PII 존재 여부와 제거 방식
- 실행한 전처리 코드 버전과 출력 Schema 버전

실제 데이터 파일은 `data/raw` 및 `data/processed`에 로컬로 두되 Git에는 포함하지 않는다.
