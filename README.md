# Nepal Bill → Tally / IRD Register Tool

Upload photos/scans/PDFs of sales or purchase bills (or register pages). Claude vision extracts the data; you review/edit it; then export:

- **IRD Sales/Purchase Register** (Excel or CSV)
- **Tally Prime import XML** (ledger masters + Sales/Purchase vouchers with VAT)
- **Tally-style Excel**

## Run on Replit
1. Import this repo into Replit (Python 3.11). Dependencies in `requirements.txt` install automatically.
2. Add **Secrets**: `ANTHROPIC_API_KEY` (required); `APP_PASSWORD` (recommended, HTTP basic-auth password so others can't spend your API credits); optional `MAX_UPLOAD_MB` (10), `RATE_LIMIT_PER_MIN` (30), `CLAUDE_MODEL`.
3. Press **Run** (`.replit` starts uvicorn on port 8000). To publish: **Deploy → Autoscale**.

## Run locally
```
pip install -r requirements.txt
ANTHROPIC_API_KEY=... uvicorn app.main:app --reload
pytest
```

## Importing into Tally Prime
Gateway of Tally → Import → Data (Vouchers), choose `tally_import.xml`. Test on a dummy company first; ledger names (Sales/Purchase/VAT) are configurable in the page. Dates import from AD; BS date and PAN go in narration/ledger.

## Notes
- Always review the table: red rows fail checks (PAN 9 digits, VAT = 13%, total, duplicate bill no, date).
- Nothing is stored on the server; files are processed in memory.
- The IRD column layout is in `app/exporters/ird.py` (`COLS`) — adjust to your template.
