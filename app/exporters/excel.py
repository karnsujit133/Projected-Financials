import io
from openpyxl import Workbook

COLS = ["Date", "Voucher Type", "Voucher No", "Party Ledger", "Party PAN", "Amount (Party)",
        "Sales/Purchase Ledger", "Taxable Amount", "VAT Ledger", "VAT Amount", "Narration"]


def to_xlsx(bills, settings) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tally Import"
    ws.append(COLS)
    for b in bills:
        sales = b.type == "sales"
        ws.append([b.date_ad, "Sales" if sales else "Purchase", b.bill_no, b.party_name, b.party_pan,
                   b.total, settings.sales_ledger if sales else settings.purchase_ledger,
                   b.taxable + b.exempt, settings.vat_ledger, b.vat, b.description])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
