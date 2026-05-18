def fmt_num(value, digits=0):
    try:
        return f"{float(value):,.{digits}f}"
    except Exception:
        return "-"


def fmt_pct(value, digits=4):
    try:
        return f"{float(value):.{digits}f}%"
    except Exception:
        return "-"
