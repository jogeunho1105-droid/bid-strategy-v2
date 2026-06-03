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
   - 오늘 투찰 우선순위 / 확인 필요 공고 자동 표시
   - 선택한 공고 1건 중심 상세 확인
   - 다운로드 엑셀에 개찰 후 피드백 입력 시트 포함

2. 낙찰데이터 분석
   - 기관별 패턴
   - 추천 사정률
   - 밀집도/과열지수
   - 시장구조 분석

## 운영 메모

- Streamlit Cloud 로컬 저장 파일은 앱 재시작 시 초기화될 수 있습니다.
- 장기 운영 시 낙찰이력과 `pattern_stats.json`은 GitHub 저장소, Google Sheets, Supabase 등 외부 저장소에 보관하는 것을 권장합니다.
- `pattern_stats.json`은 루트 또는 `data/pattern_stats.json`에 둘 수 있으며, `{"orgs": {...}}` 구조도 자동 인식합니다.
