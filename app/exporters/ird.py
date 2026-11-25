import csv
import io
from openpyxl import Workbook
from ..nepali_date import fiscal_year

COLS = ["S.N.", "Bill Date (BS)", "Bill No", "Party Name", "Party PAN", "Description", "Qty", "Unit",
        "Total Amount", "Non-taxable/Exempt", "Taxable Amount", "VAT", "Import/Export"]


def rows(bills):
    for i, b in enumerate(bills, 1):
        yield [i, b.date_bs, b.bill_no, b.party_name, b.party_pan, b.description, b.qty, b.unit,
               b.total, b.exempt, b.taxable, b.vat, "Y" if b.is_import_export else ""]


def to_xlsx(bills, kind: str) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Sales Register" if kind == "sales" else "Purchase Register"
    ws.append(COLS)
    for r in rows(bills):
        ws.append(r)
    n = len(bills) + 1
    ws.append(["", "", "", "Total", "", "", "", "", f"=SUM(I2:I{n})", f"=SUM(J2:J{n})",
               f"=SUM(K2:K{n})", f"=SUM(L2:L{n})"])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def to_csv(bills) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(COLS)
    w.writerows(rows(bills))
    return buf.getvalue().encode("utf-8-sig")
