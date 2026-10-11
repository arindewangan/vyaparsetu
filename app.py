"""VyaparSetu — invoicing + cashflow copilot for India's micro-entrepreneurs.

Theme: Financial Inclusion & Livelihoods (Social Impact Hackathon 2026).
Solo entry by Arin Dewangan (Cybs Innovations). Built during the Oct 11, 2026 sprint.

Everything here is deterministic, real computation:
- invoice math, cashflow ledger and savings projections are computed for real.
- Sathi (the advisor) is rule-based financial-literacy guidance, labeled as such.
No external APIs, no network calls, no credentials.
"""
from datetime import date
from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

THEME_SLUG = "financial-inclusion-livelihoods"
THEME_NAME = "Financial Inclusion & Livelihoods"

# ---------------------------------------------------------------- ledger state
# In-memory store (a real deployment would persist this). Documented honestly.
_ledger = {"entries": [], "seq": 0}

_INVOICE_SEQ = 0

# ------------------------------------------------- Sathi knowledge base (rules)
SATHI_RULES = [
    {
        "topic": "savings",
        "keywords": ["save", "saving", "bachat", "बचत", "save money", "savings"],
        "answer": (
            "Pay yourself first: move 10% of every day's earnings into a separate "
            "envelope or account before spending. Even Rs 50 a day becomes Rs 18,250 in a year. "
            "पहले बचत, फिर खर्च — रोज़ की कमाई का 10% अलग रखें।"
        ),
    },
    {
        "topic": "upi",
        "keywords": ["upi", "qr", "digital payment", "online payment", "phonepe", "paytm", "gpay"],
        "answer": (
            "A free UPI QR code at your stall builds trust and a payment record banks can see. "
            "Print it, laminate it, and always confirm the payment sound/notification before handing over goods. "
            "UPI QR मुफ़्त है — दुकान पर लगाएं और पेमेंट की आवाज़ ज़रूर सुनें।"
        ),
    },
    {
        "topic": "loan",
        "keywords": ["loan", "karz", "कर्ज", "udhaar", "borrow", "interest", "byaj", "ब्याज"],
        "answer": (
            "Before borrowing, check: (1) the total repayment, not just the EMI; (2) whether the "
            "interest is flat or reducing-balance. Avoid lenders charging over 3% per month. "
            "Mudra and SHG loans from banks are far cheaper than informal lenders. "
            "कर्ज़ लेने से पहले कुल चुकौती ज़रूर गिनें — 3% प्रति माह से ज़्यादा ब्याज से बचें।"
        ),
    },
    {
        "topic": "gst",
        "keywords": ["gst", "tax", "टैक्स", "invoice", "bill", "receipt"],
        "answer": (
            "You only need GST registration above Rs 40 lakh annual turnover (Rs 20 lakh for services). "
            "Below that, simple bills like the ones VyaparSetu makes are enough to look professional "
            "and build a paper trail for future bank loans. "
            "40 लाख सालाना से कम टर्नओवर पर GST ज़रूरी नहीं — साफ़-सुथरा बिल ही काफ़ी है।"
        ),
    },
    {
        "topic": "emergency",
        "keywords": ["emergency", "rainy day", "medical", "hospital", "बीमारी", "आपात"],
        "answer": (
            "Keep a 30-day emergency buffer: roughly one month of household expenses, separate from "
            "business cash. Start with Rs 100 a week if that is all you can manage — the habit matters "
            "more than the amount. घर के एक महीने के खर्च जितना आपातकालीन फंड अलग रखें।"
        ),
    },
    {
        "topic": "record",
        "keywords": ["record", "khata", "खाता", "ledger", "bahikhata", "hisab", "हिसाब", "track"],
        "answer": (
            "Write down every rupee in and out — even on paper. A 3-month record of daily income is "
            "the strongest document you can show a bank for a Mudra loan. VyaparSetu's cashflow diary "
            "does this for you automatically. हर रुपये का हिसाब लिखें — यही बैंक लोन का सबसे मज़बूत सबूत है।"
        ),
    },
]

SATHI_FALLBACK = (
    "I can help with savings (बचत), UPI payments, loans (कर्ज़), GST/tax basics, "
    "emergency funds, and keeping business records (हिसाब). Ask me about any of these! "
    "मैं बचत, UPI, कर्ज़, GST, आपातकालीन फंड और हिसाब-किताब पर मदद कर सकता हूँ।"
)


# ------------------------------------------------------------------ utilities
def _money(x):
    return round(float(x), 2)


def _validate_amount(value):
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return None, "amount must be a number"
    if amount <= 0:
        return None, "amount must be greater than zero"
    return _money(amount), None


def sathi_answer(question):
    q = (question or "").lower()
    for rule in SATHI_RULES:
        if any(k in q for k in rule["keywords"]):
            return {"answer": rule["answer"], "topic": rule["topic"], "rule_based": True}
    return {"answer": SATHI_FALLBACK, "topic": "general", "rule_based": True}


# --------------------------------------------------------------------- routes
@app.get("/")
def index():
    return render_template("index.html", theme_name=THEME_NAME)


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "theme": THEME_SLUG, "service": "vyaparsetu"})


@app.post("/api/invoice")
def create_invoice():
    """Real invoice computation: line totals, tax, grand total, invoice number."""
    global _INVOICE_SEQ
    data = request.get_json(force=True, silent=True) or {}
    items = data.get("items")
    tax_rate = data.get("tax_rate", 0)

    if not isinstance(items, list) or not items:
        return jsonify({"ok": False, "error": "items must be a non-empty list"}), 400
    try:
        tax_rate = float(tax_rate)
    except (TypeError, ValueError):
        return jsonify({"ok": False, "error": "tax_rate must be a number"}), 400
    if tax_rate < 0 or tax_rate > 100:
        return jsonify({"ok": False, "error": "tax_rate must be between 0 and 100"}), 400

    lines = []
    for i, item in enumerate(items):
        name = str(item.get("name", f"Item {i + 1}"))[:80]
        try:
            qty = float(item.get("qty", 0))
            price = float(item.get("price", 0))
        except (TypeError, ValueError):
            return jsonify({"ok": False, "error": f"item {i + 1}: qty and price must be numbers"}), 400
        if qty <= 0 or price < 0:
            return jsonify({"ok": False, "error": f"item {i + 1}: qty must be > 0, price >= 0"}), 400
        lines.append({
            "name": name,
            "qty": qty,
            "price": _money(price),
            "line_total": _money(qty * price),
        })

    subtotal = _money(sum(l["line_total"] for l in lines))
    tax = _money(subtotal * tax_rate / 100)
    total = _money(subtotal + tax)

    _INVOICE_SEQ += 1
    invoice_no = f"VST-{date.today().strftime('%Y%m%d')}-{_INVOICE_SEQ:04d}"

    return jsonify({
        "ok": True,
        "invoice_no": invoice_no,
        "date": date.today().isoformat(),
        "lines": lines,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax": tax,
        "total": total,
        "note": "Illustrative tax calculation — not tax advice.",
    })


@app.post("/api/cashflow")
def add_cashflow():
    """Record one income/expense entry; returns the entry and running balance."""
    data = request.get_json(force=True, silent=True) or {}
    kind = str(data.get("kind", "")).lower()
    if kind not in ("income", "expense"):
        return jsonify({"ok": False, "error": 'kind must be "income" or "expense"'}), 400
    amount, err = _validate_amount(data.get("amount"))
    if err:
        return jsonify({"ok": False, "error": err}), 400
    category = str(data.get("category", "general"))[:40] or "general"
    note = str(data.get("note", ""))[:140]

    _ledger["seq"] += 1
    entry = {
        "id": _ledger["seq"],
        "kind": kind,
        "amount": amount,
        "category": category,
        "note": note,
        "date": date.today().isoformat(),
    }
    _ledger["entries"].append(entry)
    return jsonify({"ok": True, "entry": entry, "balance": cashflow_balance()}), 201


def cashflow_balance():
    bal = 0.0
    for e in _ledger["entries"]:
        bal += e["amount"] if e["kind"] == "income" else -e["amount"]
    return _money(bal)


@app.get("/api/cashflow")
def cashflow_summary():
    income = _money(sum(e["amount"] for e in _ledger["entries"] if e["kind"] == "income"))
    expense = _money(sum(e["amount"] for e in _ledger["entries"] if e["kind"] == "expense"))
    by_category = {}
    for e in _ledger["entries"]:
        signed = e["amount"] if e["kind"] == "income" else -e["amount"]
        by_category[e["category"]] = _money(by_category.get(e["category"], 0) + signed)
    return jsonify({
        "ok": True,
        "entries": _ledger["entries"],
        "income": income,
        "expense": expense,
        "balance": _money(income - expense),
        "by_category": by_category,
        "count": len(_ledger["entries"]),
    })


@app.post("/api/savings")
def savings_plan():
    """Real savings projection: days/weeks/months to reach a goal."""
    data = request.get_json(force=True, silent=True) or {}
    goal, err = _validate_amount(data.get("goal_amount"))
    if err:
        return jsonify({"ok": False, "error": f"goal_amount: {err}"}), 400
    daily, err = _validate_amount(data.get("daily_savings"))
    if err:
        return jsonify({"ok": False, "error": f"daily_savings: {err}"}), 400

    import math
    days = math.ceil(goal / daily)
    return jsonify({
        "ok": True,
        "goal_amount": goal,
        "daily_savings": daily,
        "days": days,
        "weeks": round(days / 7, 1),
        "months": round(days / 30, 1),
        "one_year_projection": _money(daily * 365),
        "milestones": [
            {"at_days": min(days, d), "saved": _money(min(goal, daily * d))}
            for d in (30, 90, 180, 365) if d <= days or d == 30
        ],
        "note": "Simple projection — no interest assumed.",
    })


@app.post("/api/sathi")
def sathi():
    """Rule-based financial-literacy advisor. Deterministic; honestly labeled."""
    data = request.get_json(force=True, silent=True) or {}
    question = str(data.get("question", ""))[:500]
    if not question.strip():
        return jsonify({"ok": False, "error": "question must not be empty"}), 400
    result = sathi_answer(question)
    return jsonify({"ok": True, "question": question, **result})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
