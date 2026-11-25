import os
import secrets
import time
from collections import defaultdict

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, Response
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles

from . import extractor
from .exporters import excel, ird, tally_xml
from .schemas import Bill, ExportRequest
from .validate import validate

MAX_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
MAX_FILES = 20
RATE = int(os.getenv("RATE_LIMIT_PER_MIN", "30"))
STATIC = os.path.join(os.path.dirname(__file__), "static")

app = FastAPI(title="Nepal Bill → Tally/IRD")
basic = HTTPBasic(auto_error=False)
_hits: dict[str, list[float]] = defaultdict(list)


def auth(creds: HTTPBasicCredentials | None = Depends(basic)):
    pw = os.getenv("APP_PASSWORD")
    if not pw:
        return
    if not creds or not secrets.compare_digest(creds.password, pw):
        raise HTTPException(401, "Unauthorized", headers={"WWW-Authenticate": "Basic"})


def rate_limit(request: Request):
    ip = request.client.host if request.client else "?"
    now = time.time()
    _hits[ip] = [t for t in _hits[ip] if now - t < 60]
    if len(_hits[ip]) >= RATE:
        raise HTTPException(429, "Too many requests")
    _hits[ip].append(now)


@app.post("/api/extract", dependencies=[Depends(auth), Depends(rate_limit)])
async def extract(files: list[UploadFile] = File(...), bill_type: str = Form("sales")):
    if bill_type not in ("sales", "purchase"):
        raise HTTPException(400, "bill_type must be sales or purchase")
    if len(files) > MAX_FILES:
        raise HTTPException(400, f"Max {MAX_FILES} files")
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise HTTPException(500, "ANTHROPIC_API_KEY not set (add it in Replit Secrets)")
    bills: list[Bill] = []
    errors = []
    for f in files:
        data = await f.read()
        if len(data) > MAX_MB * 1024 * 1024:
            errors.append(f"{f.filename}: larger than {MAX_MB} MB")
            continue
        try:
            bills.extend(extractor.extract_file(data, f.content_type or "", f.filename or "", bill_type))
        except Exception as ex:  # surface per-file failure, keep others
            errors.append(f"{f.filename}: {type(ex).__name__}")
    return {"bills": validate(bills), "errors": errors}


@app.post("/api/validate", dependencies=[Depends(auth)])
def revalidate(req: ExportRequest):
    return {"bills": validate(req.bills, req.settings)}


def _kind(req: ExportRequest) -> str:
    return "purchase" if req.bills and all(b.type == "purchase" for b in req.bills) else "sales"


def _dl(content: bytes, name: str, mt: str):
    return Response(content, media_type=mt, headers={"Content-Disposition": f'attachment; filename="{name}"'})


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@app.post("/api/export/ird", dependencies=[Depends(auth)])
def export_ird(req: ExportRequest, fmt: str = "xlsx"):
    k = _kind(req)
    if fmt == "csv":
        return _dl(ird.to_csv(req.bills), f"{k}_register.csv", "text/csv")
    return _dl(ird.to_xlsx(req.bills, k), f"{k}_register.xlsx", XLSX)


@app.post("/api/export/tally-xml", dependencies=[Depends(auth)])
def export_xml(req: ExportRequest):
    return _dl(tally_xml.to_xml(req.bills, req.settings), "tally_import.xml", "application/xml")


@app.post("/api/export/excel", dependencies=[Depends(auth)])
def export_excel(req: ExportRequest):
    return _dl(excel.to_xlsx(req.bills, req.settings), "tally_import.xlsx", XLSX)


@app.get("/", dependencies=[Depends(auth)])
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


app.mount("/static", StaticFiles(directory=STATIC), name="static")
