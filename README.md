# VyaparSetu — व्यापारसेतु

**Theme:** Financial Inclusion & Livelihoods · **Event:** Social Impact Hackathon 2026 (Unstop, online)
**Solo entry:** Arin Dewangan (Cybs Innovations) · **Built:** Oct 11, 2026 (sprint build)

Invoices, cashflow and money-smarts for India's 60M+ micro-entrepreneurs — street vendors,
kirana shops, tailors, gig workers. Bilingual (English + Hindi), works in the browser, no sign-up.

## What it does (all computed live)

| Feature | What happens |
|---|---|
| 🧾 Instant Invoice | Add line items → professional bill with subtotal, illustrative tax math, invoice number. Print / save as PDF. |
| 📒 Cashflow Diary | Log income & expenses with categories → live balance, per-category totals. A 3-month record is what banks ask for with Mudra loans. |
| 🎯 Savings Planner | Goal amount + daily savings → exact days/months to goal + milestone chart. |
| 🤝 Sathi Advisor | **Rule-based** financial-literacy guidance (savings, UPI, loans, GST, emergency funds, records) in simple English + Hindi. Labeled rule-based — not a live AI model. |

## Run

```bash
python -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python app.py        # → http://localhost:5000
.venv/bin/python -m pytest     # 17 tests
```

The interactive demo is `demo/index.html` — fully client-side, so it also works as a static
GitHub Pages site. The Flask API (`/api/invoice`, `/api/cashflow`, `/api/savings`, `/api/sathi`)
mirrors the same logic for programmatic use.

## Honest tech notes

- Invoice/tax/savings math: deterministic, computed live.
- Sathi: keyword-matched rules over a curated financial-literacy knowledge base (see `SATHI_RULES` in `app.py`); responses carry `rule_based: true`.
- Cashflow ledger is in-memory on the server (a production build would persist it); the demo page persists to `localStorage`.
- No external APIs, no credentials, no network calls.
