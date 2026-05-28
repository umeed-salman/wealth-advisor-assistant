from __future__ import annotations

from collections import Counter
from statistics import mean, median, pstdev

from wealth_advisor.models import AnomalyFinding, ClientFinancialInput, Recommendation, TransactionType


def calculate_cashflow(client: ClientFinancialInput) -> float:
    income = client.monthly_income
    expenses = client.monthly_expenses
    transaction_outflows = sum(
        transaction.amount
        for transaction in client.transactions
        if transaction.transaction_type == TransactionType.debit
    )
    transaction_inflows = sum(
        transaction.amount
        for transaction in client.transactions
        if transaction.transaction_type == TransactionType.credit
    )
    return income + transaction_inflows - expenses - transaction_outflows


def calculate_savings_rate(client: ClientFinancialInput, cashflow: float) -> float:
    if client.monthly_income <= 0:
        return 0.0
    return max(cashflow, 0) / client.monthly_income


def calculate_debt_to_income(client: ClientFinancialInput) -> float:
    if client.monthly_income <= 0:
        return 0.0
    return client.liabilities / (client.monthly_income * 12)


def calculate_emergency_fund_months(client: ClientFinancialInput) -> float:
    if client.monthly_expenses <= 0:
        return 0.0
    return client.liquid_assets / client.monthly_expenses


def detect_anomalies(client: ClientFinancialInput) -> list[AnomalyFinding]:
    anomalies: list[AnomalyFinding] = []
    amounts = [transaction.amount for transaction in client.transactions]
    if len(amounts) >= 2:
        avg_amount = mean(amounts)
        median_amount = median(amounts)
        spread = pstdev(amounts) if len(amounts) >= 3 else 0.0
        threshold = avg_amount + (2.5 * spread)
        for transaction in client.transactions:
            unusually_large = transaction.amount > threshold or transaction.amount > max(median_amount * 2.5, client.monthly_income * 0.35)
            if unusually_large:
                anomalies.append(
                    AnomalyFinding(
                        severity="high",
                        title="Unusually large transaction",
                        details=f"Transaction {transaction.transaction_id} at {transaction.merchant} is materially above the client pattern.",
                        metric_name="transaction_amount",
                        observed_value=transaction.amount,
                        threshold=threshold,
                    )
                )

    category_counts = Counter(transaction.category for transaction in client.transactions)
    if category_counts.get("cash_withdrawal", 0) >= 3:
        anomalies.append(
            AnomalyFinding(
                severity="medium",
                title="Frequent cash withdrawals",
                details="Multiple cash withdrawals may indicate liquidity stress or unusual spending behavior.",
                metric_name="cash_withdrawal_count",
                observed_value=category_counts.get("cash_withdrawal", 0),
                threshold=2,
            )
        )

    if client.monthly_expenses > client.monthly_income * 1.1:
        anomalies.append(
            AnomalyFinding(
                severity="high",
                title="Negative recurring cashflow",
                details="Monthly expenses exceed income by a wide margin.",
                metric_name="monthly_expense_to_income",
                observed_value=client.monthly_expenses,
                threshold=client.monthly_income * 1.1,
            )
        )

    return anomalies


def derive_recommendation(
    client: ClientFinancialInput,
    cashflow: float,
    savings_rate: float,
    debt_to_income: float,
    emergency_fund_months: float,
    anomalies: list[AnomalyFinding],
) -> Recommendation:
    risk_flags = [anomaly.title for anomaly in anomalies]
    if debt_to_income > 0.5 or any(anomaly.severity == "high" for anomaly in anomalies):
        return Recommendation(
            action="Escalate for advisor review",
            rationale="The client profile shows elevated risk signals that merit human validation before action.",
            priority="high",
            next_steps=[
                "Review the flagged transactions with the client",
                "Confirm emergency fund coverage",
                "Reassess near-term credit usage and drawdown needs",
            ],
            risk_flags=risk_flags,
        )

    if savings_rate < 0.1:
        return Recommendation(
            action="Increase monthly savings automation",
            rationale="The client is saving less than 10% of income, leaving limited room for shocks.",
            priority="medium",
            next_steps=[
                "Set up an automatic transfer to savings",
                "Reduce discretionary spending",
                "Revisit the budget in 30 days",
            ],
            risk_flags=risk_flags,
        )

    if emergency_fund_months < 3:
        return Recommendation(
            action="Build emergency reserves",
            rationale="Emergency reserves are below the preferred buffer for stability.",
            priority="medium",
            next_steps=[
                "Target one month of expenses first",
                "Hold new investments until reserves improve",
            ],
            risk_flags=risk_flags,
        )

    return Recommendation(
        action="Maintain current plan",
        rationale="Current cashflow and reserve levels look acceptable, with no major risk signal detected.",
        priority="low",
        next_steps=["Continue periodic monitoring", "Review goals at the next planning meeting"],
        risk_flags=risk_flags,
    )
