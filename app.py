from __future__ import annotations

import streamlit as st
import plotly.express as px

from modules.data_loader import load_excel
from modules.preprocess import clean_data, filtered_valid_rate
from modules.basic_analysis import overview, group_rate_stats, monthly_trend
from modules.institution_analysis import (
    analyze_agency,
    agency_strategy_comment,
)
from modules.competitor_analysis import analyze_competitor, competitor_by_agency
from modules.strategy_engine import recommend_rate
from modules.risk_analysis import risk_summary
from utils.formatter import fmt_num, fmt_pct

st.set_page_config(page_title="입찰전략 분석 시스템 v2", layout="wide")

st.title("📊 입찰전략 분석 시스템 v2")
st.caption("낙찰데이터 기반 기관별·경쟁사별·추천 투찰률 분석")

uploaded_file = st.sidebar.file_uploader("낙찰데이터 엑셀 업로드", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("왼쪽 사이드바에서 낙찰데이터 엑셀 파일을 업로드하세요.")
    st.stop()

raw_df = load_excel(uploaded_file)
df, mapping = clean_data(raw_df)
valid_df = filtered_valid_rate(df)

st.sidebar.subheader("필터")

if "category" in valid_df.columns:
    categories = ["전체"] + sorted(valid_df["category"].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("업종/분야", categories)
else:
    selected_category = "전체"

if "agency" in valid_df.columns:
    agencies = ["전체"] + sorted(valid_df["agency"].dropna().unique().tolist())
    selected_agency = st.sidebar.selectbox("발주기관", agencies)
else:
    selected_agency = "전체"

filtered = valid_df.copy()
if selected_category != "전체" and "category" in filtered.columns:
    filtered = filtered[filtered["category"] == selected_category]
if selected_agency != "전체" and "agency" in filtered.columns:
    filtered = filtered[filtered["agency"] == selected_agency]

st.sidebar.caption(f"원본 {len(raw_df):,}건 / 유효 {len(filtered):,}건")

with st.expander("컬럼 자동 매핑 결과", expanded=False):
    st.json(mapping)

summary = overview(filtered)
risk = risk_summary(filtered)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("분석 건수", fmt_num(summary["total_count"]))
c2.metric("평균 사정률", fmt_pct(summary["avg_rate"]))
c3.metric("중앙 사정률", fmt_pct(summary["median_rate"]))
c4.metric("경쟁 강도", risk["competition_level"])
c5.metric("리스크", risk["risk_level"])

tab1, tab2, tab3, tab4, tab5 = st.tabs(["전체 흐름", "기관별", "경쟁사", "추천 투찰률", "리스크"])

with tab1:
    st.subheader("월별 사정률 흐름")
    trend = monthly_trend(filtered)
    if not trend.empty:
        fig = px.line(trend, x="월", y="평균사정률", markers=True)
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(trend, use_container_width=True)
    else:
        st.warning("월별 흐름을 계산할 수 없습니다.")

    st.subheader("업종/분야별 통계")
    cat_stats = group_rate_stats(filtered, "category", min_count=3)
    st.dataframe(cat_stats, use_container_width=True)

with tab2:
    st.subheader("기관별 사정률 통계")
    min_count = st.slider("최소 건수", 1, 30, 5, key="agency_min")
    agency_stats = analyze_agency(filtered, min_count=min_count)

    if not agency_stats.empty:
        selected_agency_detail = st.selectbox(
            "기관 상세 전략 코멘트",
            agency_stats["agency"].tolist(),
            key="agency_detail_comment",
        )

        selected_row = agency_stats[
            agency_stats["agency"] == selected_agency_detail
        ].iloc[0]

        st.info(agency_strategy_comment(selected_row))

        st.dataframe(agency_stats, use_container_width=True)

        top = agency_stats.head(20)
        fig = px.bar(top, x="agency", y="평균사정률", hover_data=["건수", "표준편차"])
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.warning("기관별 분석을 위한 데이터가 부족합니다.")

with tab3:
    st.subheader("경쟁사/낙찰업체 통계")
    min_count = st.slider("최소 낙찰 건수", 1, 30, 3, key="winner_min")
    comp_stats = analyze_competitor(filtered, min_count=min_count)
    st.dataframe(comp_stats, use_container_width=True)

    if "winner" in filtered.columns and not comp_stats.empty:
        competitor = st.selectbox("업체 상세 분석", comp_stats["winner"].tolist())
        detail = competitor_by_agency(filtered, competitor)
        st.dataframe(detail, use_container_width=True)

with tab4:
    st.subheader("기초 추천 투찰률")
    agency_arg = None if selected_agency == "전체" else selected_agency
    category_arg = None if selected_category == "전체" else selected_category
    rec = recommend_rate(valid_df, agency=agency_arg, category=category_arg)

    if rec["status"] != "산출완료":
        st.warning("추천 투찰률 산출을 위한 데이터가 부족합니다.")
    else:
        r1, r2, r3 = st.columns(3)
        r1.metric("안정형", fmt_pct(rec["stable"]))
        r2.metric("중립형", fmt_pct(rec["neutral"]))
        r3.metric("공격형", fmt_pct(rec["aggressive"]))
        r4, r5, r6 = st.columns(3)
        r4.metric("밀집도", f"{rec['density']:.1%}" if rec["density"] == rec["density"] else "-")
        r5.metric("과열지수", rec["heat_score"] if rec["heat_score"] == rec["heat_score"] else "-")
        r6.metric("실질 난이도", rec["difficulty"])

        st.info(rec["comment"])
        st.write("분석 샘플 수:", rec["sample_count"])
        st.write("최근 변동성:", fmt_pct(rec["volatility"]))
        st.caption("1차 모델은 최근 데이터 가중평균 기반입니다. 향후 기관·업체수·경쟁사 보정 모델을 추가합니다.")

with tab5:
    st.subheader("리스크 요약")
    st.json(risk)
    st.markdown(
        f"""
        - 경쟁 강도: **{risk['competition_level']}**
        - 사정률 변동성 기준 리스크: **{risk['risk_level']}**
        - 이상치 건수: **{risk['outlier_count']:,}건**
        """
    )
