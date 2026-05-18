def fmt_num(value):
    try:
        return f"{int(value):,}"
    except Exception:
        return "-"


def fmt_pct(value):
    try:
        if value is None or value != value:
            return "-"
        return f"{float(value):+.4f}%"
    except Exception:
        return "-"
