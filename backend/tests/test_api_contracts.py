from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.main import app


async def login(client: AsyncClient, email: str) -> dict[str, str]:
    response = await client.post("/api/v1/auth/login", json={"email": email})
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.mark.anyio
async def test_primary_contracts_are_available_for_each_demo_user(client: AsyncClient):
    paths = ["/dashboard/summary", "/transactions", "/budgets/current", "/budgets/recommendation", "/goals", "/forecast/cashflow?days=14", "/financial-health", "/reports/monthly", "/alerts", "/learning/recommended", "/offers/recommended"]
    for email in ("demo.student@upay.local", "demo.salary@upay.local", "demo.freelancer@upay.local"):
        headers = await login(client, email)
        for path in paths:
            assert (await client.get(f"/api/v1{path}", headers=headers)).status_code == 200


@pytest.mark.anyio
async def test_run_out_evidence_is_structured_and_complete(client: AsyncClient):
    headers = await login(client, "demo.student@upay.local")
    dashboard = (await client.get("/api/v1/dashboard/summary", headers=headers)).json()
    evidence = (await client.post("/api/v1/coach/run-out-analysis", headers=headers)).json()["evidence"]
    required = {"period", "starting_balance", "total_income", "total_expense", "net_cashflow", "largest_category_increase", "highest_spend_week", "large_transactions", "recurring_expenses"}
    assert required <= evidence.keys()
    assert dashboard["this_month"]["spending"] >= 0


@pytest.mark.anyio
async def test_budget_allocation_never_exceeds_income_or_category_total(client: AsyncClient):
    headers = await login(client, "demo.freelancer@upay.local")
    recommendation = (await client.get("/api/v1/budgets/recommendation", headers=headers)).json()
    allocated = sum(Decimal(str(value)) for value in recommendation["category_limits"].values())
    check = recommendation["allocation_check"]
    assert allocated <= Decimal(str(check["income"])) + Decimal("0.01")
    assert Decimal(str(check["spending"])) + Decimal(str(check["savings"])) + Decimal(str(check["buffer"])) <= Decimal(str(check["income"])) + Decimal("0.01")


@pytest.mark.anyio
async def test_goal_and_budget_validation_reject_incoherent_payloads(client: AsyncClient):
    headers = await login(client, "demo.student@upay.local")
    budget = await client.post("/api/v1/budgets", headers=headers, json={"total_limit": 1000, "categories": {"Food": 1001}})
    goal = await client.post("/api/v1/goals", headers=headers, json={"goal_name": "Laptop", "target_amount": 1000, "optional_current_savings": 1001, "deadline": "2030-01-01"})
    assert budget.status_code == 422
    assert goal.status_code == 422
    created = await client.post("/api/v1/goals", headers=headers, json={"goal_name": "Demo reserve", "target_amount": 5000, "optional_current_savings": 500, "deadline": "2030-01-01"})
    assert created.status_code == 200
    assert created.json()["plan"]["remaining_amount"] == 4500
