# bid-strategy-v2

입찰서류함 업로드 기반 투찰전략 생성과 낙찰데이터 분석을 통합한 Streamlit 앱입니다.

## Google Sheets DB 연동

앱은 `입찰전략_DB` Google Sheet를 원격 기준 DB로 우선 사용합니다.

- `1_낙찰이력`: 낙찰 원장
- `2_발주처패턴`: 발주처별 자동 패턴 통계
- `4_전략결과`: 앱에서 생성한 전략 결과 저장

연결되지 않으면 기존처럼 업로드 자료와 로컬 캐시를 사용합니다.

## Streamlit Cloud 설정

1. Google Cloud에서 서비스계정을 만들고 Google Sheets API를 활성화합니다.
2. 서비스계정 이메일에 `입찰전략_DB` 편집 권한을 부여합니다.
3. Streamlit Cloud 앱의 `Settings > Secrets`에 `.streamlit/secrets.toml.example` 형식으로 값을 입력합니다.
   - 추천: `[google_sheets] service_account_json = """..."""`에 Google Cloud JSON 파일 내용을 통째로 붙여 넣습니다.
   - TOML 항목으로 나눠 넣을 경우 `private_key` 줄바꿈이 깨지면 `Unable to load PEM file` 오류가 납니다.
4. `requirements.txt`에 포함된 `gspread`, `google-auth`가 설치되도록 배포합니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 운영 흐름

1. `입찰전략_DB`의 `1_낙찰이력`을 갱신합니다.
2. `2_발주처패턴`은 Google Sheets 수식으로 자동 갱신됩니다.
3. 앱에서 나라장터 입찰서류함 파일을 업로드합니다.
4. 앱은 Google Sheets 기준자료로 전략을 산출합니다.
5. 필요한 경우 `4_전략결과`에 결과를 저장합니다.
