from typing import Literal, Optional
from pydantic import BaseModel, Field


class Bill(BaseModel):
    type: Literal["sales", "purchase"] = "sales"
    bill_no: str = ""
    date_bs: str = ""          # YYYY-MM-DD (Bikram Sambat)
    date_ad: str = ""          # YYYY-MM-DD
    party_name: str = ""
    party_pan: str = ""
    description: str = ""
    qty: float = 0
    unit: str = ""
    taxable: float = 0
    exempt: float = 0
    vat: float = 0
    total: float = 0
    is_import_export: bool = False
    flags: list[str] = Field(default_factory=list)


class Settings(BaseModel):
    sales_ledger: str = "Sales"
    purchase_ledger: str = "Purchase"
    vat_ledger: str = "VAT"
    vat_rate: float = 13.0
    company: str = ""


class ExportRequest(BaseModel):
    bills: list[Bill]
    settings: Settings = Settings()
