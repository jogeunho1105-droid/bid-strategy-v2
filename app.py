from __future__ import annotations

from datetime import datetime
import io

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.basic_analysis import group_rate_stats, monthly_trend, overview
from modules.bid_strategy_legacy import (
    analyze_bid_list,
    load_history,
    load_pattern_stats,
    normalize_history,
    parse_xls,
    save_history,
)
from modules.competitor_analysis import analyze_competitor, competitor_by_agency
from modules.data_loader import load_excel
from modules.excel_exporter import make_strategy_excel
from modules.institution_analysis import analyze_agency, agency_strategy_comment
from modules.market_analysis import market_status
from modules.preprocess import clean_data, cleaning_report, filtered_valid_rate
from modules.risk_analysis import risk_summary
from modules.strategy_engine import recommend_rate
from utils.formatter import fmt_num, fmt_pct

st.set_page_config(page_title="입찰전략 분석 시스템 v2", page_icon="📊", layout="wide")

st.markdown(
    """
    <style>
    .main-header{background:linear-gradient(135deg,#1a2744,#243260);color:white;padding:20px 30px;border-radius:10px;margin-bottom:20px}
    .val-box{border-radius:8px;padding:10px 15px;font-weight:bold;font-size:1.05em;text-align:center;margin:4px 0}
    .val-pattern{background:#dbeafe;color:#1d4ed8}.val-similar{background:#dcfce7;color:#15803d}.val-trend{background:#fef9c3;color:#854d0e}.val-rec{background:#f3e8ff;color:#7c3aed}
    .val-a{background:#fee2e2;color:#991b1b;border-radius:8px;padding:10px 15px;font-weight:bold;text-align:center}
    .val-b{background:#dbeafe;color:#1d4ed8;border-radius:8px;padding:10px 15px;font-weight:bold;text-align:center}
    .val-c{background:#dcfce7;color:#15803d;border-radius:8px;padding:10px 15px;font-weight:bold;text-align:center}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="main-header">
    <h2>📊 입찰전략 분석 시스템 v2</h2>
    <p style="margin:0;opacity:0.85">입찰서류함 기반 투찰전략 생성 + 낙찰데이터 분석 통합</p>
    </div>
    """,
    unsafe_allow_html=True,
)

mode = st.sidebar.radio(
    "모드 선택",
    ["📥 투찰전략 생성", "📊 낙찰데이터 분석", "🔧 데이터 관리"],
)

# -----------------------------------------------------------------------------
# 데이터 관리
# -----------------------------------------------------------------------------
if mode == "🔧 데이터 관리":
    st.header("🔧 데이터 관리")
    st.caption("낙찰이력 파일을 업로드하면 투찰전략 생성 모드에서 ①패턴/②유사표본/③트렌드 분석에 사용됩니다.")

    hist = load_history()
    if hist is not None:
        valid = hist[hist["예가/기초(0%)"].notna() & (hist["예가/기초(0%)"].abs() < 10)]
        c1, c2, c3 = st.columns(3)
        c1.metric("현재 낙찰이력", f"{len(valid):,}건")
        c2.metric("발주기관", f"{valid['발주기관'].nunique() if '발주기관' in valid.columns else 0:,}개")
        c3.metric("평균 사정률", f"{valid['예가/기초(0%)'].mean():+.4f}%")
    else:
        st.warning("현재 저장된 낙찰이력이 없습니다.")

    uploaded = st.file_uploader("낙찰데이터 엑셀 업로드", type=["xlsx", "xls"])
    if uploaded:
        try:
            df_new = pd.read_excel(uploaded)
            df_new = normalize_history(df_new)
            required = ["발주기관", "공고명", "기초금액", "예가/기초(0%)"]
            missing = [c for c in required if c not in df_new.columns]
            if missing:
                st.error(f"필수 컬럼이 없습니다: {missing}")
            else:
                save_history(df_new)
                df_v = df_new[df_new["예가/기초(0%)"].notna() & (df_new["예가/기초(0%)"].abs() < 10)]
                st.success("낙찰이력 저장 완료")
                st.dataframe(df_v.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"업로드 처리 오류: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 투찰전략 생성
# -----------------------------------------------------------------------------
if mode == "📥 투찰전략 생성":
    st.header("📥 입찰서류함 기반 투찰전략 생성")

    hist = load_history()
    if hist is None:
        st.warning("낙찰이력이 없습니다. 먼저 '데이터 관리'에서 낙찰데이터를 업로드하세요.")
        df_c = None
    else:
        df_c = hist[hist["예가/기초(0%)"].notna() & (hist["예가/기초(0%)"].abs() < 10)].copy()
        c1, c2, c3 = st.columns(3)
        c1.metric("낙찰이력", f"{len(df_c):,}건")
        c2.metric("발주기관", f"{df_c['발주기관'].nunique() if '발주기관' in df_c.columns else 0:,}개")
        c3.metric("평균 사정률", f"{df_c['예가/기초(0%)'].mean():+.4f}%")

    pattern_stats = load_pattern_stats()
    xls_file = st.file_uploader("나라장터 입찰서류함 xls/xlsx 업로드", type=["xls", "xlsx"])

    if not xls_file:
        st.info("입찰서류함 파일을 업로드하면 자동으로 투찰전략을 산출합니다.")
        st.stop()

    try:
        raw_bytes = xls_file.read()
        bids = parse_xls(raw_bytes, xls_file.name)
        if not bids:
            st.error("입찰 건을 읽을 수 없습니다. 나라장터 입찰서류함 파일인지 확인하세요.")
            st.stop()
    except Exception as e:
        st.error(f"파일 읽기 오류: {e}")
        st.stop()

    st.success(f"입찰 건 {len(bids)}건 확인")
    results = analyze_bid_list(bids, df_c, pattern_stats)

    rows = []
    for row in results:
        b = row["bid"]; a1 = row["a1"]; a2 = row["a2"]; a3 = row["a3"]; tp = row["three_pt"]
        lo, hi = row["range_lo"], row["range_hi"]
        grade = a1.get("grade", "?") if a1 else "?"
        tp_str = f"A:{tp['pt_a']:+.2f} B:{tp['pt_b']:+.4f} C:{tp['pt_c']:+.2f} ({tp['cover']}%)" if tp else "-"
        rows.append({
            "No": b["no"],
            "공고명": b["name"][:40] + "…" if len(b["name"]) > 40 else b["name"],
            "발주기관": b["org"].replace("한국전력공사 ", "한전 "),
            "기초(억)": f"{b['base_억']:.4f}" if b["base"] > 0 else "미정",
            "마감": b["deadline"],
            "①패턴": f"{a1['pred']:+.4f}%" if a1 else "없음",
            "②유사표본": f"{a2['pred']:+.4f}%" if a2 else "없음",
            "③트렌드": f"{a3['pred']:+.4f}%" if a3 else "없음",
            "권장하한": f"{lo:+.4f}%" if lo is not None else "-",
            "권장상한": f"{hi:+.4f}%" if hi is not None else "-",
            "수렴도": row["conv_lbl"],
            "등급": grade,
            "3포인트": tp_str,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    st.subheader("건별 상세")
    for row in results:
        b = row["bid"]; a1 = row["a1"]; a2 = row["a2"]; a3 = row["a3"]; tp = row["three_pt"]
        lo, hi = row["range_lo"], row["range_hi"]
        with st.expander(f"No.{b['no']} {b['name']} | {b['org']} | {b['base_억']:.4f}억"):
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                v = f"{a1['pred']:+.4f}%" if a1 else "이력없음"
                st.markdown(f'<div class="val-box val-pattern">①패턴<br>{v}</div>', unsafe_allow_html=True)
                if a1: st.caption(f"n={a1['n']} | {a1['trend']} | {a1['pattern']} | 등급 {a1['grade']}")
            with c2:
                v = f"{a2['pred']:+.4f}%" if a2 else "이력없음"
                st.markdown(f'<div class="val-box val-similar">②유사표본<br>{v}</div>', unsafe_allow_html=True)
                if a2: st.caption(f"n={a2['n']} | 평균 {a2['mean']:+.4f}%")
            with c3:
                v = f"{a3['pred']:+.4f}%" if a3 else "이력없음"
                st.markdown(f'<div class="val-box val-trend">③트렌드<br>{v}</div>', unsafe_allow_html=True)
                if a3: st.caption(f"최근{a3['recent_n']}건 | drift {a3['drift']:+.4f}%")
            with c4:
                if lo is not None:
                    st.markdown(f'<div class="val-box val-rec">권장구간<br>{lo:+.4f}%~{hi:+.4f}%</div>', unsafe_allow_html=True)
                    if b["base"] > 0:
                        st.caption(f"하한 {int(b['base']*(100+lo)/100):,}원")
                        st.caption(f"상한 {int(b['base']*(100+hi)/100):,}원")
                else:
                    st.warning("데이터 부족")
            if tp:
                st.markdown("---")
                st.write(f"3개 업체 분산투찰 전략: **{tp['bias']}** / {tp['detail']} / 커버율 {tp['cover']}%")
                ca, cb, cc = st.columns(3)
                with ca:
                    amt = f"<br>{int(b['base']*(100+tp['pt_a'])/100):,}원" if b["base"] > 0 else ""
                    st.markdown(f'<div class="val-a">업체A<br>{tp["pt_a"]:+.2f}%{amt}</div>', unsafe_allow_html=True)
                with cb:
                    amt = f"<br>{int(b['base']*(100+tp['pt_b'])/100):,}원" if b["base"] > 0 else ""
                    st.markdown(f'<div class="val-b">업체B<br>{tp["pt_b"]:+.4f}%{amt}</div>', unsafe_allow_html=True)
                with cc:
                    amt = f"<br>{int(b['base']*(100+tp['pt_c'])/100):,}원" if b["base"] > 0 else ""
                    st.markdown(f'<div class="val-c">업체C<br>{tp["pt_c"]:+.2f}%{amt}</div>', unsafe_allow_html=True)

    excel_buf = make_strategy_excel(results)
    today_str = datetime.now().strftime("%Y%m%d")
    st.download_button(
        "투찰전략 엑셀 다운로드",
        data=excel_buf,
        file_name=f"투찰전략_{today_str}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
    st.stop()

# -----------------------------------------------------------------------------
# 낙찰데이터 분석
# -----------------------------------------------------------------------------
st.header("📊 낙찰데이터 분석")
uploaded_file = st.sidebar.file_uploader("낙찰데이터 엑셀 업로드", type=["xlsx", "xls"])

if uploaded_file is None:
    st.info("왼쪽 사이드바에서 낙찰데이터 엑셀 파일을 업로드하세요.")
    st.stop()

raw_df = load_excel(uploaded_file)
df, mapping = clean_data(raw_df)
valid_df = filtered_valid_rate(df)

st.sidebar.subheader("필터")
cat_col = "category_clean" if "category_clean" in valid_df.columns else "category"
agency_col = "agency_clean" if "agency_clean" in valid_df.columns else "agency"

if cat_col in valid_df.columns:
    categories = ["전체"] + sorted(valid_df[cat_col].dropna().unique().tolist())
    selected_category = st.sidebar.selectbox("업종/분야", categories)
else:
    selected_category = "전체"

if agency_col in valid_df.columns:
    agencies = ["전체"] + sorted(valid_df[agency_col].dropna().unique().tolist())
    selected_agency = st.sidebar.selectbox("발주기관", agencies)
else:
    selected_agency = "전체"

filtered = valid_df.copy()
if selected_category != "전체" and cat_col in filtered.columns:
    filtered = filtered[filtered[cat_col] == selected_category]
if selected_agency != "전체" and agency_col in filtered.columns:
    filtered = filtered[filtered[agency_col] == selected_agency]

st.sidebar.caption(f"원본 {len(raw_df):,}건 / 유효 {len(filtered):,}건")

with st.expander("컬럼 자동 매핑 및 정제 리포트", expanded=False):
    st.json(mapping)
    st.json(cleaning_report(df))

summary = overview(filtered)
risk = risk_summary(filtered)

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("분석 건수", fmt_num(summary["total_count"]))
c2.metric("평균 사정률", fmt_pct(summary["avg_rate"]))
c3.metric("중앙 사정률", fmt_pct(summary["median_rate"]))
c4.metric("경쟁 강도", risk["competition_level"])
c5.metric("리스크", risk["risk_level"])

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["전체 흐름", "기관별", "경쟁사", "추천 투찰률", "리스크", "시장구조"])

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
    cat_stats = group_rate_stats(filtered, cat_col, min_count=3) if cat_col in filtered.columns else pd.DataFrame()
    st.dataframe(cat_stats, use_container_width=True)

with tab2:
    st.subheader("기관별 사정률 통계")
    min_count = st.slider("최소 건수", 1, 30, 5, key="agency_min")
    agency_stats = analyze_agency(filtered, min_count=min_count)
    if not agency_stats.empty:
        selected_agency_detail = st.selectbox("기관 상세 전략 코멘트", agency_stats["agency"].tolist(), key="agency_detail_comment")
        selected_row = agency_stats[agency_stats["agency"] == selected_agency_detail].iloc[0]
        st.info(agency_strategy_comment(selected_row))
        st.dataframe(agency_stats, use_container_width=True)
        top = agency_stats.head(20)
        fig = px.bar(top, x="agency", y="평균사정률", hover_data=["건수", "표준편차"])
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("기관별 분석을 위한 데이터가 부족합니다.")

with tab3:
    st.subheader("경쟁사/낙찰업체 통계")
    st.caption("현재 경쟁사 분석은 참고용입니다. 실제 관계사/경쟁사 투찰 분석 데이터가 보강되면 고도화합니다.")
    min_count = st.slider("최소 낙찰 건수", 1, 30, 3, key="winner_min")
    comp_stats = analyze_competitor(filtered, min_count=min_count)
    st.dataframe(comp_stats, use_container_width=True)
    if not comp_stats.empty:
        competitor = st.selectbox("업체 상세 분석", comp_stats["winner"].tolist())
        detail = competitor_by_agency(filtered, competitor)
        st.dataframe(detail, use_container_width=True)

with tab4:
    st.subheader("추천 사정률")
    agency_arg = None if selected_agency == "전체" else selected_agency
    category_arg = None if selected_category == "전체" else selected_category
    rec = recommend_rate(valid_df, agency=agency_arg, category=category_arg)
    if rec["status"] != "산출완료":
        st.warning("추천 사정률 산출을 위한 데이터가 부족합니다.")
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

with tab5:
    st.subheader("리스크 요약")
    st.json(risk)

with tab6:
    st.subheader("시장구조 분석")
    n_market = st.slider("최근 비교 구간", 10, 60, 30, key="market_n")
    market = market_status(filtered, n=n_market)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("시장 상태", market["market_status"])
    m2.metric("최근 방향", market["trend"].get("direction", "판단불가"))
    m3.metric("변동성", market["volatility"].get("volatility_status", "판단불가"))
    m4.metric("경쟁 흐름", market["bidder"].get("bidder_status", "판단불가"))
    st.info(market["comment"])
    st.write("### 세부 지표")
    st.json(market)
