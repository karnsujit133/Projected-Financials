import re
from .nepali_date import norm_digits, normalize_date
from .schemas import Bill, Settings


def validate(bills: list[Bill], settings: Settings | None = None) -> list[Bill]:
    s = settings or Settings()
    seen: dict[tuple, int] = {}
    for b in bills:
        b.flags = []
        b.bill_no = norm_digits(b.bill_no).strip()
        b.party_pan = re.sub(r"\D", "", norm_digits(b.party_pan))
        if b.date_bs or b.date_ad:
            bs, ad = normalize_date(b.date_bs or b.date_ad)
            b.date_bs, b.date_ad = bs, ad
        if not b.date_bs:
            b.flags.append("Missing/invalid date")
        if not b.bill_no:
            b.flags.append("Missing bill no")
        if not b.party_name:
            b.flags.append("Missing party name")
        if b.party_pan and len(b.party_pan) != 9:
            b.flags.append("PAN must be 9 digits")
        if not b.party_pan and b.taxable > 50000:
            b.flags.append("PAN missing on large bill")
        if abs(b.vat - b.taxable * s.vat_rate / 100) > max(1.0, b.taxable * 0.005) and b.vat:
            b.flags.append(f"VAT is not {s.vat_rate:g}% of taxable")
        if abs(b.total - (b.taxable + b.exempt + b.vat)) > 1.0:
            b.flags.append("Total != taxable + exempt + VAT")
        key = (b.type, b.bill_no, b.party_pan or b.party_name)
        if b.bill_no:
            if key in seen:
                b.flags.append("Duplicate bill no")
            seen[key] = 1
    return bills
