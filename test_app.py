"""Tests for VyaparSetu — every route, happy paths and validation errors."""
import math

import pytest

from app import app, _ledger

client = app.test_client()


@pytest.fixture(autouse=True)
def clean_ledger():
    _ledger["entries"].clear()
    _ledger["seq"] = 0
    yield
    _ledger["entries"].clear()
    _ledger["seq"] = 0


def test_root_returns_200():
    r = client.get("/")
    assert r.status_code == 200
    assert b"VyaparSetu" in r.data


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["theme"] == "financial-inclusion-livelihoods"


def test_invoice_math():
    r = client.post("/api/invoice", json={
        "items": [
            {"name": "Samosa", "qty": 20, "price": 15},
            {"name": "Chai", "qty": 10, "price": 10},
        ],
        "tax_rate": 5,
    })
    assert r.status_code == 200
    body = r.get_json()
    assert body["ok"] is True
    assert body["subtotal"] == 400.0
    assert body["tax"] == 20.0
    assert body["total"] == 420.0
    assert body["invoice_no"].startswith("VST-")
    assert len(body["lines"]) == 2
    assert body["lines"][0]["line_total"] == 300.0


def test_invoice_zero_tax():
    r = client.post("/api/invoice", json={"items": [{"name": "X", "qty": 2, "price": 50}]})
    body = r.get_json()
    assert body["total"] == 100.0
    assert body["tax"] == 0.0


def test_invoice_rejects_empty_items():
    r = client.post("/api/invoice", json={"items": []})
    assert r.status_code == 400


def test_invoice_rejects_bad_qty():
    r = client.post("/api/invoice", json={"items": [{"name": "X", "qty": -2, "price": 50}]})
    assert r.status_code == 400


def test_invoice_rejects_crazy_tax():
    r = client.post("/api/invoice", json={
        "items": [{"name": "X", "qty": 1, "price": 50}], "tax_rate": 150})
    assert r.status_code == 400


def test_cashflow_add_and_summary():
    r1 = client.post("/api/cashflow", json={"kind": "income", "amount": 1500, "category": "sales"})
    assert r1.status_code == 201
    r2 = client.post("/api/cashflow", json={"kind": "expense", "amount": 400, "category": "stock"})
    assert r2.status_code == 201
    body = client.get("/api/cashflow").get_json()
    assert body["income"] == 1500.0
    assert body["expense"] == 400.0
    assert body["balance"] == 1100.0
    assert body["by_category"]["sales"] == 1500.0
    assert body["count"] == 2


def test_cashflow_rejects_bad_kind():
    r = client.post("/api/cashflow", json={"kind": "lottery", "amount": 100})
    assert r.status_code == 400


def test_cashflow_rejects_negative_amount():
    r = client.post("/api/cashflow", json={"kind": "income", "amount": -50})
    assert r.status_code == 400


def test_savings_plan():
    r = client.post("/api/savings", json={"goal_amount": 10000, "daily_savings": 100})
    body = r.get_json()
    assert r.status_code == 200
    assert body["days"] == 100
    assert body["one_year_projection"] == 36500.0
    assert body["months"] == round(100 / 30, 1)


def test_savings_plan_rounds_up_days():
    r = client.post("/api/savings", json={"goal_amount": 1000, "daily_savings": 300})
    assert r.get_json()["days"] == math.ceil(1000 / 300) == 4


def test_savings_rejects_zero_goal():
    r = client.post("/api/savings", json={"goal_amount": 0, "daily_savings": 100})
    assert r.status_code == 400


def test_sathi_matches_savings_topic():
    r = client.post("/api/sathi", json={"question": "how can I save money daily?"})
    body = r.get_json()
    assert r.status_code == 200
    assert body["topic"] == "savings"
    assert body["rule_based"] is True
    assert "10%" in body["answer"]


def test_sathi_matches_hindi_keyword():
    r = client.post("/api/sathi", json={"question": "मुझे बचत के बारे में बताओ"})
    body = r.get_json()
    assert body["topic"] == "savings"


def test_sathi_fallback():
    r = client.post("/api/sathi", json={"question": "what is the capital of France?"})
    body = r.get_json()
    assert body["topic"] == "general"
    assert body["rule_based"] is True


def test_sathi_rejects_empty_question():
    r = client.post("/api/sathi", json={"question": "   "})
    assert r.status_code == 400
