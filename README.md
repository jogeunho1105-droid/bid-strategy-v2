# bid-strategy-v2-stable

기존 운영 앱은 그대로 유지하고, `bid_app_stable.py`를 기반으로 만든 v2 테스트용 Streamlit 앱입니다.

## 목적

- 기존 앱과 동일한 투찰전략 기능을 v2 앱에서 별도로 테스트
- 운영 앱 중단 없이 화면, 전략 로직, 데이터 저장 방식을 검증
- 최종 안정화 후 운영 앱으로 전환

## 포함 기능

- 나라장터 입찰서류함 `xls/xlsx` 업로드
- ① 패턴 범위 비교
  - 한국전력공사 전체 패턴
  - 동일 발주처 전체 패턴
  - 한국전력공사 감리/진단 전체 패턴
  - 동일 발주처 감리/진단 패턴
- 유사표본 분석
- 최근 트렌드 분석
- 건별 차트
- 투찰전략 엑셀 다운로드
- 관리자 모드 낙찰이력 업로드

## 배포 파일

GitHub repo 루트에는 아래 파일과 폴더가 보여야 합니다.

```text
app.py
requirements.txt
README.md
.streamlit/secrets.toml.example
```

## Streamlit Secrets

Streamlit Cloud의 `App settings > Secrets`에 아래 값을 입력합니다.

```toml
ADMIN_PWD = "원하는_관리자_비밀번호"
```

`ADMIN_PWD`를 설정하지 않으면 코드 기본값을 사용하므로, 테스트 앱이라도 반드시 Secrets에 직접 지정하는 것을 권장합니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 운영 메모

현재 버전은 기존 안정판과 동일하게 `data/history.pkl`, `data/pattern_stats.json` 로컬 저장 방식을 사용합니다. Streamlit Cloud에서는 앱 재시작 시 데이터가 초기화될 수 있으므로, 장기 운영판에서는 Google Sheets `입찰전략_DB` 연동을 추가하는 것이 좋습니다.
