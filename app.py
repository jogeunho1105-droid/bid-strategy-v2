from __future__ import annotations

from datetime import datetime
import io

import pandas as pd
import plotly.express as px
import streamlit as st

from modules.basic_analysis import group_rate_stats, monthly_trend, overview
from modules.bid_strategy_legacy import (
    analyze_bid_list,
    is_kepco,
    load_history,
    load_pattern_stats,
    normalize_history,
    parse_xls,
    save_history,
)
from modules.competitor_analysis import analyze_competitor, competitor_by_agency
from modules.data_loader import load_excel
from modules.excel_exporter import make_strategy_excel
from modules.google_sheets_db import (
    append_strategy_results,
    google_sheets_config_status,
    load_google_sheets_reference,
)
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
    .status-ok{background:#dcfce7;color:#166534;padding:3px 8px;border-radius:999px;font-weight:700}
    .status-warn{background:#fef3c7;color:#92400e;padding:3px 8px;border-radius:999px;font-weight:700}
    .status-risk{background:#fee2e2;color:#991b1b;padding:3px 8px;border-radius:999px;font-weight:700}
    .compact-note{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:10px 12px}
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
    ["📥 투찰전략 생성", "📊 낙찰데이터 분석", "🔧 기준자료 관리"],
)


def _history_from_state_or_disk():
    if "history_df" in st.session_state:
        return st.session_state["history_df"]
    hist = load_history()
    if hist is not None:
        st.session_state["history_df"] = hist
    return hist


def _store_history(df):
    hist = normalize_history(df)
    st.session_state["history_df"] = hist
    save_history(hist)
    return hist


def _reference_from_remote_or_local(force_refresh=False):
    remote_hist, remote_patterns, remote_status = load_google_sheets_reference(force_refresh=force_refresh)
    st.session_state["remote_db_status"] = remote_status
    if remote_hist is not None:
        hist = normalize_history(remote_hist)
        st.session_state["history_df"] = hist
        st.session_state["remote_pattern_stats"] = remote_patterns
        return hist, remote_patterns, remote_status

    hist = _history_from_state_or_disk()
    local_patterns = load_pattern_stats()
    return hist, local_patterns, remote_status


def _show_remote_status(status):
    if status.get("connected"):
        st.success(
            f"Google Sheets DB 연결됨: 낙찰이력 {status.get('history_rows', 0):,}건, "
            f"패턴 {status.get('pattern_count', 0):,}개"
        )
        st.caption(f"마지막 읽기: {status.get('loaded_at', '-')}")
        return

    if not status.get("configured"):
        cfg = google_sheets_config_status()
        st.info(
            "Google Sheets 서비스계정이 아직 설정되지 않았습니다. "
            "Streamlit Secrets에 서비스계정 정보를 넣으면 이 앱이 입찰전략_DB를 직접 읽습니다."
        )
        st.caption(f"대상 Spreadsheet ID: {cfg.get('spreadsheet_id')}")
    else:
        st.warning(f"Google Sheets DB 연결 실패: {status.get('error', '알 수 없는 오류')}")


def _analysis_count(row):
    return sum(1 for key in ["a1", "a2", "a3"] if row.get(key))


def _quality_label(row):
    b = row["bid"]
    grade = row["a1"].get("grade", "?") if row.get("a1") else "?"
    flags = []
    if b["base"] <= 0:
        flags.append("기초금액 확인")
    if _analysis_count(row) < 2:
        flags.append("분석값 부족")
    if grade == "D":
        flags.append("신뢰도 D")
    if row["range_lo"] is None:
        flags.append("권장구간 없음")
    if "분산" in str(row["conv_lbl"]):
        flags.append("분산큼")
    if not flags:
        return "정상"
    return ", ".join(flags)


def _priority_score(row):
    grade = row["a1"].get("grade", "?") if row.get("a1") else "?"
    score = 0
    score += _analysis_count(row) * 2
    score += {"A": 3, "B": 2, "C": 1, "D": -2}.get(grade, 0)
    score += 2 if row.get("three_pt") else 0
    score += 2 if row["range_lo"] is not None else -2
    if "높음" in str(row["conv_lbl"]):
        score += 2
    if "분산" in str(row["conv_lbl"]):
        score -= 2
    if row["bid"]["base"] <= 0:
        score -= 3
    return score


def _status_badge(label):
    if label == "정상":
        return '<span class="status-ok">정상</span>'
    if "분산" in label or "신뢰도 D" in label or "분석값 부족" in label:
        return f'<span class="status-risk">{label}</span>'
    return f'<span class="status-warn">{label}</span>'

# -----------------------------------------------------------------------------
# 기준자료 관리
# -----------------------------------------------------------------------------
if mode == "🔧 기준자료 관리":
    st.header("🔧 기준자료 관리")
    st.caption("투찰전략 생성에 사용할 낙찰이력 기준자료를 확인하고 교체하는 화면입니다.")
    st.info("운영 기준자료는 Google Sheets의 입찰전략_DB를 우선 사용합니다. 연결되지 않으면 기존 업로드/로컬 캐시 방식으로 동작합니다.")

    if st.button("Google Sheets DB 다시 읽기", use_container_width=True):
        hist, pattern_stats, remote_status = _reference_from_remote_or_local(force_refresh=True)
    else:
        hist, pattern_stats, remote_status = _reference_from_remote_or_local()
    _show_remote_status(remote_status)

    if hist is not None:
        valid = hist[hist["예가/기초(0%)"].notna() & (hist["예가/기초(0%)"].abs() < 10)]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("현재 낙찰이력", f"{len(valid):,}건")
        c2.metric("발주기관", f"{valid['발주기관'].nunique() if '발주기관' in valid.columns else 0:,}개")
        c3.metric("평균 사정률", f"{valid['예가/기초(0%)'].mean():+.4f}%")
        c4.metric("패턴통계", f"{len(pattern_stats):,}개")
    else:
        st.warning("현재 저장된 낙찰이력이 없습니다.")
        st.metric("패턴통계", f"{len(pattern_stats):,}개")

    uploaded = st.file_uploader("낙찰데이터 엑셀 업로드", type=["xlsx", "xls"])
    st.caption("업로드는 임시/보조 기능입니다. 여러 PC 공용 운영자료는 Google Sheets의 1_낙찰이력을 갱신하세요.")
    if uploaded:
        try:
            df_new = pd.read_excel(uploaded)
            df_new = _store_history(df_new)
            required = ["발주기관", "공고명", "기초금액", "예가/기초(0%)"]
            missing = [c for c in required if c not in df_new.columns]
            if missing:
                st.error(f"필수 컬럼이 없습니다: {missing}")
            else:
                df_v = df_new[df_new["예가/기초(0%)"].notna() & (df_new["예가/기초(0%)"].abs() < 10)]
                st.success("기준자료 저장 완료. 이제 투찰전략 생성에서 이 데이터를 사용합니다.")
                st.dataframe(df_v.head(20), use_container_width=True)
        except Exception as e:
            st.error(f"업로드 처리 오류: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 투찰전략 생성
# -----------------------------------------------------------------------------
if mode == "📥 투찰전략 생성":
    st.header("📥 입찰서류함 기반 투찰전략 생성")

    refresh_db = st.sidebar.button("DB 새로고침")
    hist, pattern_stats, remote_status = _reference_from_remote_or_local(force_refresh=refresh_db)
    with st.sidebar.expander("DB 연결 상태", expanded=False):
        _show_remote_status(remote_status)

    if hist is None:
        st.warning("낙찰이력이 없습니다. 먼저 '낙찰데이터 분석' 또는 '기준자료 관리'에서 낙찰데이터를 업로드하세요.")
        df_c = None
    else:
        df_c = hist[hist["예가/기초(0%)"].notna() & (hist["예가/기초(0%)"].abs() < 10)].copy()
        c1, c2, c3 = st.columns(3)
        c1.metric("낙찰이력", f"{len(df_c):,}건")
        c2.metric("발주기관", f"{df_c['발주기관'].nunique() if '발주기관' in df_c.columns else 0:,}개")
        c3.metric("평균 사정률", f"{df_c['예가/기초(0%)'].mean():+.4f}%")

    if pattern_stats:
        st.caption(f"패턴통계 DB {len(pattern_stats):,}개 발주기관 연결됨")
    elif df_c is None:
        st.error("패턴통계와 낙찰이력이 모두 없어 전략 정확도가 크게 낮아집니다. 먼저 데이터 관리에서 낙찰데이터를 업로드하세요.")

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
        quality = _quality_label(row)
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
            "확인필요": quality,
            "우선점수": _priority_score(row),
        })
    result_df = pd.DataFrame(rows).sort_values(["우선점수", "No"], ascending=[False, True])

    ok_count = int((result_df["확인필요"] == "정상").sum()) if not result_df.empty else 0
    risk_count = len(result_df) - ok_count
    three_pt_count = sum(1 for row in results if row.get("three_pt"))
    no_range_count = sum(1 for row in results if row["range_lo"] is None)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("전략 대상", f"{len(results):,}건")
    m2.metric("정상", f"{ok_count:,}건")
    m3.metric("확인 필요", f"{risk_count:,}건")
    m4.metric("3포인트 적용", f"{three_pt_count:,}건")
    if no_range_count:
        st.warning(f"권장구간이 없는 공고가 {no_range_count}건 있습니다. 기초금액, 발주기관, 낙찰이력 표본을 확인하세요.")

    st.subheader("오늘 투찰 우선순위")
    st.dataframe(
        result_df.drop(columns=["우선점수"]),
        use_container_width=True,
        hide_index=True,
        column_config={
            "공고명": st.column_config.TextColumn(width="large"),
            "발주기관": st.column_config.TextColumn(width="medium"),
            "3포인트": st.column_config.TextColumn(width="medium"),
            "확인필요": st.column_config.TextColumn(width="medium"),
        },
    )

    st.subheader("선택 공고 상세")
    result_lookup = {row["bid"]["no"]: row for row in results}
    detail_options = [
        f"No.{row['bid']['no']} | {_quality_label(row)} | {row['bid']['name'][:48]}"
        for row in sorted(results, key=_priority_score, reverse=True)
    ]
    selected_detail = st.selectbox("상세 확인 공고", detail_options)
    selected_no = int(selected_detail.split("|", 1)[0].replace("No.", "").strip())
    row = result_lookup[selected_no]
    b = row["bid"]; a1 = row["a1"]; a2 = row["a2"]; a3 = row["a3"]; tp = row["three_pt"]
    lo, hi = row["range_lo"], row["range_hi"]
    st.markdown(
        f"<div class='compact-note'><b>No.{b['no']} {b['name']}</b><br>"
        f"{b['org']} | 기초 {b['base_억']:.4f}억 | 마감 {b['deadline']} | "
        f"{_status_badge(_quality_label(row))}</div>",
        unsafe_allow_html=True,
    )
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        v = f"{a1['pred']:+.4f}%" if a1 else "이력없음"
        st.markdown(f'<div class="val-box val-pattern">①패턴<br>{v}</div>', unsafe_allow_html=True)
        if a1:
            st.caption(f"n={a1['n']} | {a1['trend']} | {a1['pattern']} | 등급 {a1['grade']} | {a1.get('source','')}")
    with c2:
        v = f"{a2['pred']:+.4f}%" if a2 else "이력없음"
        st.markdown(f'<div class="val-box val-similar">②유사표본<br>{v}</div>', unsafe_allow_html=True)
        if a2:
            st.caption(f"n={a2['n']} | 평균 {a2['mean']:+.4f}%")
            if a2.get("fallback"):
                st.caption(f"대체표본: {a2.get('fallback_note','')}")
    with c3:
        v = f"{a3['pred']:+.4f}%" if a3 else "이력없음"
        st.markdown(f'<div class="val-box val-trend">③트렌드<br>{v}</div>', unsafe_allow_html=True)
        if a3:
            st.caption(f"최근{a3['recent_n']}건 | drift {a3['drift']:+.4f}%")
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
    elif is_kepco(b["org"]):
        st.warning("한전 공고이지만 3포인트 적용 조건에서 제외되었습니다. 수의/소액수의/전자견적 여부를 확인하세요.")

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
    if remote_status.get("connected"):
        with st.expander("Google Sheets에 전략결과 저장", expanded=False):
            created_by = st.text_input("저장자", value="", placeholder="예: 홍길동")
            if st.button("4_전략결과에 저장", type="secondary", use_container_width=True):
                try:
                    saved = append_strategy_results(results, created_by=created_by.strip())
                    st.success(f"Google Sheets 4_전략결과에 {saved.get('saved', 0):,}건 저장했습니다.")
                except Exception as e:
                    st.error(f"전략결과 저장 실패: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 낙찰데이터 분석
# -----------------------------------------------------------------------------
st.header("📊 낙찰데이터 분석")
uploaded_file = st.sidebar.file_uploader("낙찰데이터 엑셀 업로드", type=["xlsx", "xls"], key="analysis_history_upload")

if uploaded_file is not None:
    raw_df = load_excel(uploaded_file)
    st.session_state["analysis_raw_df"] = raw_df
    st.session_state["analysis_file_name"] = uploaded_file.name
    try:
        _store_history(raw_df)
        st.success("낙찰데이터를 분석자료와 투찰전략 기준자료로 보관했습니다.")
    except Exception:
        st.info("분석자료로 보관했습니다. 투찰전략 기준자료 저장은 컬럼 확인 후 가능합니다.")
elif "analysis_raw_df" in st.session_state:
    raw_df = st.session_state["analysis_raw_df"]
    st.caption(f"현재 세션에 보관된 파일 사용 중: {st.session_state.get('analysis_file_name', '낙찰데이터')}")
else:
    st.info("왼쪽 사이드바에서 낙찰데이터 엑셀 파일을 업로드하세요.")
    st.stop()

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
