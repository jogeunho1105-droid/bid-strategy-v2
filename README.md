# bid-strategy-v2 merged

낙찰데이터 기반 분석 시스템과 기존 입찰서류함 업로드 기반 투찰전략 생성 기능을 통합한 Streamlit 앱입니다.

## 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## 주요 기능

1. 투찰전략 생성
   - 나라장터 입찰서류함 xls/xlsx 업로드
   - 낙찰이력 업로드
   - 예가/기초(%) 기준 분석
   - ①패턴 / ②유사표본 / ③트렌드
   - 권장 하한/상한
   - 한전 3포인트 분산투찰
   - 투찰전략 xlsx 다운로드

2. 낙찰데이터 분석
   - 기관별 패턴
   - 추천 사정률
   - 밀집도/과열지수
   - 시장구조 분석
