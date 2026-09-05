# Dataset Quality Gates

정규화된 데이터는 `make validate-data`를 통과해야 Synthetic 생성, RAG 인덱싱 또는 모델 평가에 사용할 수 있다. 검증 기준은 `data/contracts/quality-gates.json`에서 Dataset Snapshot별로 관리한다.

## 검증 범위

- 정규화 보고서 존재 여부
- Snapshot별 기대 행 수
- JSONL 실제 행 수와 보고서 일치 여부
- 출력 파일 SHA-256 일치 여부
- 상담 데이터의 구조화 PII 잔존 0건
- 상담 Train/Validation 중복 제외 건수
- 금융상품 중복 제거와 소비자 개인 행 미저장
- BPI 정규화 Event 중복 0건
- Banking77 77개 Label 및 범위 분류 완전성

## 실행

```bash
make validate-data
```

결과는 `data/processed/quality-gate.json`에 기록되며 원본·정규화 데이터와 마찬가지로 Git에 저장하지 않는다. 하나라도 실패하면 명령은 종료 코드 1을 반환한다.

행 수가 바뀌었을 때 기대값만 임의로 수정해서는 안 된다. 먼저 원본 Dataset 리비전, Manifest, Normalizer 버전과 품질 변화의 원인을 확인한 뒤 새로운 Snapshot 계약으로 갱신한다.
