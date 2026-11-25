from xml.sax.saxutils import escape as e, quoteattr


def _ledger(name, parent, pan="", extra=""):
    pan_x = f"<INCOMETAXNUMBER>{e(pan)}</INCOMETAXNUMBER>" if pan else ""
    return (f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><LEDGER NAME={quoteattr(name)} ACTION="Create">'
            f'<NAME>{e(name)}</NAME><PARENT>{parent if '&' in parent else e(parent)}</PARENT>{extra}{pan_x}</LEDGER></TALLYMESSAGE>')


def to_xml(bills, settings) -> bytes:
    """Single import envelope: ledger masters first, then vouchers.
    Sales: party Dr, sales/VAT Cr.  Purchase: purchase/VAT Dr, party Cr."""
    out = ['<ENVELOPE><HEADER><TALLYREQUEST>Import Data</TALLYREQUEST></HEADER><BODY><IMPORTDATA>'
           '<REQUESTDESC><REPORTNAME>Vouchers</REPORTNAME><STATICVARIABLES>']
    if settings.company:
        out.append(f"<SVCURRENTCOMPANY>{e(settings.company)}</SVCURRENTCOMPANY>")
    out.append("</STATICVARIABLES></REQUESTDESC><REQUESTDATA>")

    has_sales = any(b.type == "sales" for b in bills)
    has_purch = any(b.type == "purchase" for b in bills)
    if has_sales:
        out.append(_ledger(settings.sales_ledger, "Sales Accounts"))
    if has_purch:
        out.append(_ledger(settings.purchase_ledger, "Purchase Accounts"))
    out.append(_ledger(settings.vat_ledger, "Duties &amp; Taxes"))
    seen = set()
    for b in bills:
        if b.party_name and b.party_name not in seen:
            seen.add(b.party_name)
            out.append(_ledger(b.party_name, "Sundry Debtors" if b.type == "sales" else "Sundry Creditors", b.party_pan))

    for b in bills:
        sales = b.type == "sales"
        vt = "Sales" if sales else "Purchase"
        main = settings.sales_ledger if sales else settings.purchase_ledger
        base = round(b.taxable + b.exempt, 2)
        sgn = 1 if sales else -1  # Tally: debit amounts negative
        entries = [(b.party_name, "Yes" if sales else "No", -sgn * round(b.total, 2)),
                   (main, "No" if sales else "Yes", sgn * base)]
        if b.vat:
            entries.append((settings.vat_ledger, "No" if sales else "Yes", sgn * round(b.vat, 2)))
        v = [f'<TALLYMESSAGE xmlns:UDF="TallyUDF"><VOUCHER VCHTYPE={quoteattr(vt)} ACTION="Create">',
             f"<DATE>{b.date_ad.replace('-', '')}</DATE><VOUCHERTYPENAME>{vt}</VOUCHERTYPENAME>",
             f"<VOUCHERNUMBER>{e(b.bill_no)}</VOUCHERNUMBER><REFERENCE>{e(b.bill_no)}</REFERENCE>",
             f"<PARTYLEDGERNAME>{e(b.party_name)}</PARTYLEDGERNAME>",
             f"<NARRATION>{e(f'BS {b.date_bs} PAN {b.party_pan}')}</NARRATION>"]
        for name, dr, amt in entries:
            v.append(f"<ALLLEDGERENTRIES.LIST><LEDGERNAME>{e(name)}</LEDGERNAME>"
                     f"<ISDEEMEDPOSITIVE>{dr}</ISDEEMEDPOSITIVE><AMOUNT>{amt:.2f}</AMOUNT></ALLLEDGERENTRIES.LIST>")
        v.append("</VOUCHER></TALLYMESSAGE>")
        out.append("".join(v))
    out.append("</REQUESTDATA></IMPORTDATA></BODY></ENVELOPE>")
    return "".join(out).encode("utf-8")
