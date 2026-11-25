import base64
import json
import os
import pymupdf as fitz
import anthropic

from .schemas import Bill

MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

PROMPT = """You are reading Nepali tax invoices / bills or pages of a sales or purchase register.
Extract EVERY bill/row you can see (a register page may hold many). Rules:
- Convert Devanagari digits to ASCII digits.
- Dates: copy as written. Nepali bills use Bikram Sambat (BS), e.g. 2081/04/15; put it in date_bs as YYYY-MM-DD. If only an English (AD) date is shown, put it in date_ad.
- party_pan: 9-digit PAN/VAT no. of the customer (sales) or supplier (purchase). Empty if absent.
- taxable: amount subject to VAT (before VAT). exempt: non-taxable/exempt amount. vat: VAT amount (13% normally). total: grand total.
- If the document shows only a total including VAT and no breakup, compute taxable = total/1.13 and vat = total - taxable.
- Never invent values; leave empty/0 when unreadable.
Always respond by calling the record_bills tool (use an empty list if no bill is visible)."""

TOOL = {
    "name": "record_bills",
    "description": "Record all bills found in the image.",
    "input_schema": {
        "type": "object",
        "properties": {
            "bills": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "bill_no": {"type": "string"},
                        "date_bs": {"type": "string"},
                        "date_ad": {"type": "string"},
                        "party_name": {"type": "string"},
                        "party_pan": {"type": "string"},
                        "description": {"type": "string"},
                        "qty": {"type": "number"},
                        "unit": {"type": "string"},
                        "taxable": {"type": "number"},
                        "exempt": {"type": "number"},
                        "vat": {"type": "number"},
                        "total": {"type": "number"},
                        "is_import_export": {"type": "boolean"},
                    },
                    "required": ["bill_no", "date_bs", "date_ad", "party_name", "party_pan", "description",
                                 "qty", "unit", "taxable", "exempt", "vat", "total", "is_import_export"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["bills"],
        "additionalProperties": False,
    },
    "strict": True,
}


def to_images(data: bytes, content_type: str, filename: str = "") -> list[tuple[str, bytes]]:
    """Return [(media_type, bytes)] — PDFs rendered to PNG pages."""
    if content_type == "application/pdf" or filename.lower().endswith(".pdf"):
        doc = fitz.open(stream=data, filetype="pdf")
        return [("image/png", p.get_pixmap(dpi=150).tobytes("png")) for p in doc]
    mt = content_type if content_type in ("image/jpeg", "image/png", "image/webp", "image/gif") else "image/jpeg"
    return [(mt, data)]


def extract_image(media_type: str, data: bytes, bill_type: str, client=None) -> list[Bill]:
    client = client or anthropic.Anthropic()
    resp = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        tools=[TOOL],
        tool_choice={"type": "auto"},  # forced tool_choice is rejected (400) on Sonnet 5.5
        output_config={"effort": "low"},  # plain transcription; keeps cost down
        messages=[{
            "role": "user",
            "content": [
                {"type": "image", "source": {"type": "base64", "media_type": media_type,
                                             "data": base64.b64encode(data).decode()}},
                {"type": "text", "text": PROMPT},
            ],
        }],
    )
    out: list[Bill] = []
    for block in resp.content:
        if block.type == "tool_use":
            for raw in block.input.get("bills", []):
                raw = {k: v for k, v in raw.items() if k in Bill.model_fields}
                out.append(Bill(type=bill_type, **raw))
    return out


def extract_file(data: bytes, content_type: str, filename: str, bill_type: str, client=None) -> list[Bill]:
    bills: list[Bill] = []
    for mt, img in to_images(data, content_type, filename):
        bills.extend(extract_image(mt, img, bill_type, client))
    return bills
