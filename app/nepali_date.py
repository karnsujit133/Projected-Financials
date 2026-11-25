import datetime as dt
import re
import nepali_datetime

_DEV = str.maketrans("०१२३४५६७८९", "0123456789")


def norm_digits(s: str) -> str:
    return (s or "").translate(_DEV)


def _parse(s: str):
    m = re.match(r"^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})$", norm_digits(s).strip())
    return tuple(int(x) for x in m.groups()) if m else None


def bs_to_ad(s: str) -> str:
    p = _parse(s)
    if not p:
        return ""
    try:
        return nepali_datetime.date(*p).to_datetime_date().isoformat()
    except Exception:
        return ""


def ad_to_bs(s: str) -> str:
    p = _parse(s)
    if not p:
        return ""
    try:
        d = nepali_datetime.date.from_datetime_date(dt.date(*p))
        return f"{d.year:04d}-{d.month:02d}-{d.day:02d}"
    except Exception:
        return ""


def normalize_date(s: str) -> tuple[str, str]:
    """Return (bs, ad). Year >= 2000 and < 2057 treated as AD, otherwise BS."""
    p = _parse(s)
    if not p:
        return "", ""
    if p[0] < 2057:
        ad = f"{p[0]:04d}-{p[1]:02d}-{p[2]:02d}"
        return ad_to_bs(ad), ad
    bs = f"{p[0]:04d}-{p[1]:02d}-{p[2]:02d}"
    return bs, bs_to_ad(bs)


def fiscal_year(bs: str) -> str:
    p = _parse(bs)
    if not p:
        return ""
    y = p[0] if p[1] >= 4 else p[0] - 1  # FY starts Shrawan (month 4)
    return f"{y}/{str(y + 1)[-2:]}"
