import io
import xml.etree.ElementTree as ET
from types import SimpleNamespace
from fastapi.testclient import TestClient
from openpyxl import load_workbook

from app import extractor
from app.main import app
from app.nepali_date import ad_to_bs, bs_to_ad, fiscal_year, norm_digits, normalize_date
from app.schemas import Bill, Settings
from app.validate import validate
from app.exporters import ird, tally_xml, excel


def mk(**k):
    d = dict(type="sales", bill_no="101", date_bs="2081-04-15", party_name="ABC Pvt Ltd",
             party_pan="123456789", taxable=1000, vat=130, total=1130)
    d.update(k)
    return Bill(**d)


def test_dates():
    assert bs_to_ad("2081-04-01") == "2024-07-16"
    assert ad_to_bs("2024-07-16") == "2081-04-01"
    assert normalize_date("२०८१/०४/०१") == ("2081-04-01", "2024-07-16")
    assert norm_digits("१२३") == "123"
    assert fiscal_year("2081-04-01") == "2081/82" and fiscal_year("2081-03-31") == "2080/81"


def test_validate():
    ok, bad, dup = validate([mk(), mk(bill_no="102", party_pan="12", vat=50), mk()])
    assert not ok.flags and ok.date_ad == "2024-07-30"
    assert any("PAN" in f for f in bad.flags) and any("VAT" in f for f in bad.flags)
    assert "Duplicate bill no" in dup.flags


def test_exporters():
    bills = validate([mk(), mk(type="purchase", bill_no="P1", party_name="A & B \"Co\"")])
    s = Settings()
    root = ET.fromstring(tally_xml.to_xml(bills, s))
    vs = root.findall(".//VOUCHER")
    assert len(vs) == 2
    for v in vs:
        assert abs(sum(float(a.find("AMOUNT").text) for a in v.findall("ALLLEDGERENTRIES.LIST"))) < 0.01
    assert vs[0].find("ALLLEDGERENTRIES.LIST/AMOUNT").text == "-1130.00"
    ws = load_workbook(io.BytesIO(ird.to_xlsx(bills, "sales"))).active
    assert ws["D2"].value == "ABC Pvt Ltd"
    assert load_workbook(io.BytesIO(excel.to_xlsx(bills, s))).active["B3"].value == "Purchase"
    assert b"Bill No" in ird.to_csv(bills)


class FakeClient:
    class messages:
        @staticmethod
        def create(**kw):
            blk = SimpleNamespace(type="tool_use", input={"bills": [
                {"bill_no": "१०१", "date_bs": "२०८१/०४/१५", "party_name": "X", "party_pan": "123456789",
                 "taxable": 1000, "vat": 130, "total": 1130, "junk": 1}]})
            return SimpleNamespace(content=[blk])


def test_extract_mock():
    b = extractor.extract_image("image/png", b"x", "purchase", FakeClient())
    assert b[0].type == "purchase"
    assert validate(b)[0].bill_no == "101" and not b[0].flags


def test_api(monkeypatch):
    c = TestClient(app)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "k")
    monkeypatch.setattr(extractor, "extract_file", lambda *a, **k: [mk()])
    r = c.post("/api/extract", files=[("files", ("a.png", b"x", "image/png"))], data={"bill_type": "sales"})
    assert r.status_code == 200 and len(r.json()["bills"]) == 1
    body = {"bills": r.json()["bills"], "settings": {}}
    for p in ("ird", "ird?fmt=csv", "tally-xml", "excel"):
        assert c.post("/api/export/" + p, json=body).status_code == 200
    assert c.get("/").status_code == 200
    monkeypatch.setenv("APP_PASSWORD", "pw")
    assert c.get("/").status_code == 401
