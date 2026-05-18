from __future__ import annotations

import io
import json
import os
from datetime import datetime

import numpy as np
import pandas as pd
import xlrd

DATA_DIR = "data"
HISTORY_FILE = os.path.join(DATA_DIR, "history.pkl")
PATTERN_FILE = os.path.join(DATA_DIR, "pattern_stats.json")

THREE_PT = {
    "한국전력공사 경기본부": {"bias":"음수↓","detail":"음60%/중13%/양27%","pt_a":-0.40,"pt_c":+0.20,"cover":63,"cover_r":73,"note":"음수편향 강함"},
    "한국전력공사 부산울산본부": {"bias":"음수↓","detail":"음55%/중23%/양23%","pt_a":-0.25,"pt_c":+0.35,"cover":62,"cover_r":87,"note":"최근커버 87% 우수"},
    "한국전력공사 대전세종충남본부": {"bias":"균형","detail":"음39%/중29%/양32%","pt_a":-0.35,"pt_c":+0.25,"cover":64,"cover_r":77,"note":"균형형. 최근커버 77%"},
    "한국전력공사 인천본부": {"bias":"양수↑","detail":"음31%/중12%/양56%","pt_a":-0.35,"pt_c":+0.30,"cover":64,"cover_r":75,"note":"양수편향. C포인트 주력"},
    "한국전력공사 서울본부": {"bias":"양수↑","detail":"음20%/중20%/양60%","pt_a":-0.35,"pt_c":+0.25,"cover":64,"cover_r":70,"note":"양수편향 매우 강함"},
    "한국전력공사 경북본부": {"bias":"음수↓","detail":"음47%/중18%/양35%","pt_a":-0.40,"pt_c":+0.20,"cover":63,"cover_r":71,"note":"음수편향. 표준전략"},
    "한국전력공사 경남본부": {"bias":"음수↓","detail":"음50%/중30%/양20%","pt_a":-0.40,"pt_c":+0.25,"cover":62,"cover_r":100,"note":"최근커버 100%!"},
    "한국전력공사 광주전남본부": {"bias":"음수↓","detail":"음52%/중10%/양38%","pt_a":-0.40,"pt_c":+0.20,"cover":61,"cover_r":67,"note":"수익성 주의"},
    "한국전력공사 대구본부": {"bias":"음수↓","detail":"음52%/중12%/양36%","pt_a":-0.45,"pt_c":+0.15,"cover":63,"cover_r":72,"note":"A포인트 깊게"},
    "한국전력공사 강원본부": {"bias":"음수↓","detail":"음53%/중13%/양33%","pt_a":-0.40,"pt_c":+0.20,"cover":63,"cover_r":93,"note":"최근커버 93% 우수"},
    "한국전력공사 전북본부": {"bias":"음수↓","detail":"음56%/중11%/양33%","pt_a":-0.30,"pt_c":+0.35,"cover":62,"cover_r":0,"note":"음수편향 표준"},
    "한국전력공사 충북본부": {"bias":"균형","detail":"음47%/중3%/양50%","pt_a":-0.30,"pt_c":+0.30,"cover":62,"cover_r":0,"note":"균형형"},
    "한국전력공사 경기북부본부": {"bias":"음수↓","detail":"음53%/중11%/양37%","pt_a":-0.30,"pt_c":+0.30,"cover":58,"cover_r":58,"note":"커버율 다소 낮음"},
    "한국전력공사 남서울본부": {"bias":"균형","detail":"음50%/중0%/양50%","pt_a":-0.50,"pt_c":+0.10,"cover":62,"cover_r":0,"note":"A포인트 깊게"},
    "한국전력공사 제주본부": {"bias":"음수↓","detail":"음50%/중15%/양35%","pt_a":-0.40,"pt_c":+0.20,"cover":60,"cover_r":0,"note":"제주 표준"},
}

AMT_BRACKETS = {
    "~0.5억": {"range":(0,0.5),"adj":+0.0013,"note":"소형"},
    "0.5~1억": {"range":(0.5,1.0),"adj":+0.0045,"note":"소형"},
    "1~2억": {"range":(1.0,2.0),"adj":+0.0424,"note":"유리 ↑"},
    "2~5억": {"range":(2.0,5.0),"adj":-0.0295,"note":"보수적 ↓"},
    "5~10억": {"range":(5.0,10.0),"adj":+0.0398,"note":"대형"},
    "10억+": {"range":(10.0,9999),"adj":+0.0373,"note":"대형"},
}

DIAG_KWS = ["광학", "초음파", "VLF", "PD", "콘크리트"]


def is_kepco(org):
    return "한국전력공사" in str(org)


def is_diag(name):
    return any(kw in str(name) for kw in DIAG_KWS)


def is_supervision(name):
    return "감리" in str(name)


def is_three_pt_applicable(org, name):
    if not is_kepco(org):
        return False
    if any(kw in str(name) for kw in ["수의", "소액수의", "전자견적"]):
        return False
    return True


def get_amt_info(base_억):
    for label, info in AMT_BRACKETS.items():
        lo, hi = info["range"]
        if lo <= base_억 < hi:
            return label, info["adj"], info["note"]
    return "미정", 0.0, ""


def get_three_pt(org, pred):
    if org in THREE_PT:
        d = THREE_PT[org]
        return {
            "pt_a": d["pt_a"], "pt_b": round(pred, 4), "pt_c": d["pt_c"],
            "bias": d["bias"], "detail": d["detail"], "cover": d["cover"],
            "cover_r": d["cover_r"], "note": d["note"], "found": True,
        }
    return {"pt_a":-0.40,"pt_b":round(pred,4),"pt_c":+0.20,"bias":"균형","detail":"이력 부족","cover":60,"cover_r":0,"note":"기본값 적용","found":False}


def normalize_history(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "예가/기초(%)" in out.columns and "예가/기초(0%)" not in out.columns:
        out["예가/기초(0%)"] = out["예가/기초(%)"]
    if "예가/기초" in out.columns and "예가/기초(0%)" not in out.columns:
        out["예가/기초(0%)"] = out["예가/기초"]
    if "예가/기초(0%)" in out.columns:
        r = pd.to_numeric(out["예가/기초(0%)"].astype(str).str.replace("%", "", regex=False), errors="coerce")
        med = r.dropna().median() if r.notna().any() else 0
        if 90 <= med <= 110:
            r = r - 100
        elif 0.9 <= med <= 1.1:
            r = (r - 1) * 100
        out["예가/기초(0%)"] = r
    if "기초금액" in out.columns:
        out["기초금액"] = pd.to_numeric(out["기초금액"].astype(str).str.replace(",", "", regex=False), errors="coerce")
    for c in ["발주기관", "공고명"]:
        if c in out.columns:
            out[c] = out[c].astype(str).str.strip()
    return out


def load_history():
    if os.path.exists(HISTORY_FILE):
        return pd.read_pickle(HISTORY_FILE)
    return None


def save_history(df):
    os.makedirs(DATA_DIR, exist_ok=True)
    normalize_history(df).to_pickle(HISTORY_FILE)


def load_pattern_stats():
    if os.path.exists(PATTERN_FILE):
        with open(PATTERN_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def parse_xls(file_bytes, filename=""):
    bids = []
    is_xlsx = filename.lower().endswith(".xlsx") if filename else False
    if not is_xlsx:
        try:
            is_xlsx = file_bytes[:2] == b"PK"
        except Exception:
            is_xlsx = False
    if is_xlsx:
        import openpyxl
        wb = openpyxl.load_workbook(io.BytesIO(file_bytes), read_only=True, data_only=True)
        ws = wb.active
        rows_data = list(ws.iter_rows(values_only=True))
        wb.close()
        if len(rows_data) < 3:
            return bids
        headers = [str(c) if c is not None else "" for c in rows_data[1]]
        for row_vals in rows_data[2:]:
            row = {headers[i]: row_vals[i] for i in range(min(len(headers), len(row_vals)))}
            if not row.get("번호"):
                continue
            try: base = float(str(row.get("기초금액") or 0).replace(",", ""))
            except Exception: base = 0
            bids.append({"no":int(float(row["번호"])), "name":str(row.get("공고명") or ""), "bid_no":str(row.get("공고번호") or ""), "base":base, "base_억":round(base/1e8,4) if base else 0, "deadline":str(row.get("투찰마감") or ""), "org":str(row.get("발주기관") or ""), "region":str(row.get("지역") or "")})
    else:
        wb = xlrd.open_workbook(file_contents=file_bytes, ignore_workbook_corruption=True)
        ws = wb.sheets()[0]
        headers = [ws.cell_value(1, c) for c in range(ws.ncols)]
        for r in range(2, ws.nrows):
            row = {headers[c]: ws.cell_value(r, c) for c in range(ws.ncols)}
            if not row.get("번호"):
                continue
            try: base = float(str(row.get("기초금액") or 0).replace(",", ""))
            except Exception: base = 0
            bids.append({"no":int(float(row["번호"])), "name":str(row.get("공고명", "")), "bid_no":str(row.get("공고번호", "")), "base":base, "base_억":round(base/1e8,4) if base else 0, "deadline":str(row.get("투찰마감", "")), "org":str(row.get("발주기관", "")), "region":str(row.get("지역", ""))})
    return bids


def analyze_pattern(org, df_c, pattern_stats):
    if org in pattern_stats:
        st_d = pattern_stats[org]
        return {"pred":st_d.get("pred",0),"conservative":st_d.get("conservative",0),"aggressive":st_d.get("aggressive",0),"trend":st_d.get("trend","→횡보"),"pattern":st_d.get("pattern","무작위패턴").replace("패턴", ""),"autocorr":st_d.get("autocorr",0),"last_val":st_d.get("last_val",0),"r5":st_d.get("r5",0),"r10":st_d.get("r10",0),"mean":st_d.get("mean",0),"std":st_d.get("std",0.5),"n":st_d.get("n",0),"w5":st_d.get("w5",0.25),"w10":st_d.get("w10",0.20),"wm":st_d.get("wm",0.55),"grade":st_d.get("grade","C"),"mae":st_d.get("mae",0.5),"recent10":st_d.get("recent10",[]),"all_vals":None,"source":"패턴통계DB"}
    if df_c is None or "예가/기초(0%)" not in df_c.columns:
        return None
    sub = df_c[df_c["발주기관"] == org]["예가/기초(0%)"].dropna().values
    if len(sub) < 5:
        return None
    n = len(sub); mean = np.mean(sub); std = np.std(sub)
    r5 = np.mean(sub[-5:]); r10 = np.mean(sub[-10:]) if n >= 10 else mean
    ac = float(np.corrcoef(sub[:-1], sub[1:])[0,1]) if n >= 3 and np.std(sub[:-1]) > 0 and np.std(sub[1:]) > 0 else 0
    coef = float(np.polyfit(np.arange(min(20,n)), sub[-min(20,n):], 1)[0]) if n >= 3 else 0
    trend = "↑상승" if coef > 0.02 else "↓하락" if coef < -0.02 else "→횡보"
    pattern = "연속성" if ac > 0.2 else "반전" if ac < -0.2 else "무작위"
    pred = 0.25*r5 + 0.20*r10 + 0.55*mean
    lv = float(sub[-1])
    adj = lv*abs(ac)*0.2 if pattern == "연속성" else -lv*abs(ac)*0.3 if pattern == "반전" else 0.0
    pred_final = round(pred + adj, 4)
    errs = []
    for i in range(min(10, n//2), n):
        hist = sub[:i]
        p = 0.25*np.mean(hist[-5:]) + 0.20*(np.mean(hist[-10:]) if i >= 10 else np.mean(hist)) + 0.55*np.mean(hist)
        errs.append(abs(p - sub[i]))
    mae = np.mean(errs) if errs else 0.5
    grade = "A" if mae < 0.35 else "B" if mae < 0.45 else "C" if mae < 0.55 else "D"
    return {"pred":pred_final,"conservative":round(pred_final-std*0.4,4),"aggressive":round(pred_final+std*0.4,4),"trend":trend,"pattern":pattern,"autocorr":round(ac,4),"last_val":round(lv,4),"r5":round(r5,4),"r10":round(r10,4),"mean":round(mean,4),"std":round(std,4),"n":n,"w5":0.25,"w10":0.20,"wm":0.55,"grade":grade,"mae":round(mae,4),"recent10":[round(float(v),4) for v in sub[-10:]],"all_vals":sub.tolist(),"source":"직접계산"}


def analyze_similar(name, base_원, df_c):
    if df_c is None or base_원 <= 0 or "예가/기초(0%)" not in df_c.columns:
        return None
    kws = [kw for kw in ["PD","VLF","감리","진단","설계","측정","광학","초음파","콘크리트"] if kw in name]
    if not kws:
        kws = ["감리"]
    mask = pd.Series(False, index=df_c.index)
    for kw in kws:
        mask = mask | df_c["공고명"].astype(str).str.contains(kw, na=False)
    sim = df_c[mask & (df_c["기초금액"] >= base_원*0.5) & (df_c["기초금액"] <= base_원*1.5)]
    if len(sim) < 3:
        sim = df_c[mask & (df_c["기초금액"] >= base_원*0.3) & (df_c["기초금액"] <= base_원*2.0)]
    fallback = False
    if len(sim) < 3:
        if is_diag(name):
            sim = df_c[df_c["발주기관"].astype(str).str.contains("한국전력공사", na=False) & df_c["공고명"].astype(str).str.contains("|".join(DIAG_KWS), na=False)]
        elif is_supervision(name):
            sim = df_c[df_c["발주기관"].astype(str).str.contains("한국전력공사", na=False) & df_c["공고명"].astype(str).str.contains("감리", na=False)]
        fallback = True
    if len(sim) < 3:
        return None
    vals = sim["예가/기초(0%)"].dropna().values
    if len(vals) < 3:
        return None
    weights = np.linspace(0.5, 1.5, len(vals))
    co = sim["업체수"].mean() if "업체수" in sim.columns else None
    return {"pred":round(float(np.average(vals, weights=weights)),4),"n":len(vals),"mean":round(float(np.mean(vals)),4),"std":round(float(np.std(vals)),4),"avg_companies":round(float(co),1) if co is not None and not np.isnan(float(co)) else None,"keywords":kws,"fallback":fallback,"fallback_note":"분야 전체평균 대체" if fallback else ""}


def analyze_trend(org, df_c):
    if df_c is None or "예가/기초(0%)" not in df_c.columns:
        return None
    sub = df_c[df_c["발주기관"] == org]
    vals = sub["예가/기초(0%)"].dropna().values
    if len(vals) < 5:
        return None
    rn = max(5, len(vals)//4)
    recent = vals[-rn:]; older = vals[:-rn]
    rm = float(np.mean(recent)); om = float(np.mean(older)) if len(older) > 0 else rm
    drift = rm - om; r3 = vals[-3:] if len(vals) >= 3 else vals
    co = sub["업체수"].tail(rn).mean() if "업체수" in sub.columns else None
    raw_pred = rm + drift*0.3
    if abs(raw_pred) < 0.02:
        raw_pred = float(np.mean(vals))
    return {"pred":round(raw_pred,4),"recent_mean":round(rm,4),"drift":round(drift,4),"recent_n":rn,"recent3_mean":round(float(np.mean(r3)),4),"avg_companies":round(float(co),1) if co is not None and not np.isnan(float(co)) else None}


def recommend_range(a1, a2, a3):
    vals = [v["pred"] for v in [a1,a2,a3] if v]
    if not vals:
        return None, None
    mv = np.mean(vals); sv = np.std(vals) if len(vals) > 1 else 0.1
    return round(mv - sv*0.5, 4), round(mv + sv*0.5, 4)


def convergence_score(a1, a2, a3):
    vals = [v["pred"] for v in [a1,a2,a3] if v]
    if len(vals) < 2:
        return None, "데이터부족"
    sv = np.std(vals)
    if sv < 0.05: return sv, "★★★ 높음"
    if sv < 0.10: return sv, "★★☆ 보통"
    if sv < 0.20: return sv, "★☆☆ 낮음"
    return sv, "⚠️ 분산큼"


def analyze_bid_list(bids, df_c, pattern_stats):
    results = []
    for b in bids:
        a1 = analyze_pattern(b["org"], df_c, pattern_stats)
        a2 = analyze_similar(b["name"], b["base"], df_c)
        a3 = analyze_trend(b["org"], df_c)
        lo, hi = recommend_range(a1, a2, a3)
        conv_std, conv_lbl = convergence_score(a1, a2, a3)
        amt_lbl, amt_adj, amt_note = get_amt_info(b["base_억"])
        pred_val = a1["pred"] if a1 else 0.0
        tp = get_three_pt(b["org"], pred_val) if is_three_pt_applicable(b["org"], b["name"]) else None
        results.append({"bid":b,"a1":a1,"a2":a2,"a3":a3,"range_lo":lo,"range_hi":hi,"conv_std":conv_std,"conv_lbl":conv_lbl,"amt_lbl":amt_lbl,"amt_adj":amt_adj,"amt_note":amt_note,"three_pt":tp})
    return results
