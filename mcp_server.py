# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "fastmcp>=2.0",
#     "plaid-python>=29.0",
#     "python-dotenv>=1.0",
# ]
# ///
"""MCP server exposing Plaid financial data as tools for LM Studio."""

import os
import signal
import sys
from datetime import UTC, datetime, timedelta


def _handle_shutdown(signum: int, frame: object) -> None:
    """Handle Ctrl+C gracefully without async traceback noise."""
    sys.stderr.write("\nMCP server stopped.\n")
    os._exit(0)


signal.signal(signal.SIGINT, _handle_shutdown)

from fastmcp import FastMCP
from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.country_code import CountryCode
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.investments_transactions_get_request import InvestmentsTransactionsGetRequest
from plaid.model.investments_transactions_get_request_options import InvestmentsTransactionsGetRequestOptions
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_recurring_get_request import TransactionsRecurringGetRequest

from plaid_utils import (
    FeedEntry,
    append_feed_entry,
    clear_feed,
    get_plaid_client,
    load_access_tokens,
)

mcp = FastMCP("plaid-finance")


@mcp.tool()
def get_accounts() -> list[dict]:
    """Return a list of all linked accounts with institution name, account name, and type."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_accounts: list[dict] = []

    for label, token in tokens.items():
        try:
            request = AccountsGetRequest(access_token=token)
            response = client.accounts_get(request)
            item = response.item
            institution_name = label

            if item.institution_id:
                try:
                    inst_request = InstitutionsGetByIdRequest(
                        institution_id=item.institution_id,
                        country_codes=[CountryCode("US")],
                    )
                    inst_response = client.institutions_get_by_id(inst_request)
                    institution_name = inst_response.institution.name
                except Exception:
                    pass

            for account in response.accounts:
                all_accounts.append({
                    "institution_name": institution_name,
                    "account_name": account.name,
                    "account_type": str(account.type.value),
                    "account_id": account.account_id,
                })
        except Exception as e:
            all_accounts.append({"error": f"Failed to fetch accounts for {label}: {e}"})

    append_feed_entry(FeedEntry(
        tool_name="get_accounts",
        params={},
        result_count=len(all_accounts),
    ))
    return all_accounts


@mcp.tool()
def get_balances() -> list[dict]:
    """Return current balances for all linked accounts across all tokens."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_balances: list[dict] = []

    for label, token in tokens.items():
        try:
            request = AccountsBalanceGetRequest(access_token=token)
            response = client.accounts_balance_get(request)

            for account in response.accounts:
                balance = account.balances
                all_balances.append({
                    "account_name": account.name,
                    "current_balance": balance.current,
                    "available_balance": balance.available,
                    "currency": balance.iso_currency_code or "USD",
                })
        except Exception as e:
            all_balances.append({"error": f"Failed to fetch balances for {label}: {e}"})

    append_feed_entry(FeedEntry(
        tool_name="get_balances",
        params={},
        result_count=len(all_balances),
    ))
    return all_balances


@mcp.tool()
def get_transactions(start_date: str, end_date: str) -> list[dict]:
    """Return transactions across all linked accounts for a date range.

    Args:
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
    """
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_transactions: list[dict] = []

    for label, token in tokens.items():
        try:
            request = TransactionsGetRequest(
                access_token=token,
                start_date=datetime.strptime(start_date, "%Y-%m-%d").date(),
                end_date=datetime.strptime(end_date, "%Y-%m-%d").date(),
            )
            response = client.transactions_get(request)

            for txn in response.transactions:
                all_transactions.append({
                    "date": str(txn.date),
                    "merchant_name": txn.merchant_name or txn.name,
                    "amount": txn.amount,
                    "category": txn.personal_finance_category.primary if txn.personal_finance_category else None,
                })
        except Exception as e:
            all_transactions.append({"error": f"Failed to fetch transactions for {label}: {e}"})

    all_transactions.sort(key=lambda t: t.get("date", ""), reverse=True)

    append_feed_entry(FeedEntry(
        tool_name="get_transactions",
        params={"start_date": start_date, "end_date": end_date},
        result_count=len(all_transactions),
    ))
    return all_transactions


@mcp.tool()
def get_recurring_transactions() -> list[dict]:
    """Return auto-detected recurring transactions (subscriptions, bills, etc.) across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_recurring: list[dict] = []

    for label, token in tokens.items():
        try:
            request = TransactionsRecurringGetRequest(access_token=token)
            response = client.transactions_recurring_get(request)

            for stream in response.inflow_streams:
                all_recurring.append({
                    "type": "inflow",
                    "merchant_name": stream.merchant_name or stream.description,
                    "amount": stream.average_amount.amount if stream.average_amount else None,
                    "frequency": str(stream.frequency.value) if stream.frequency else None,
                    "last_date": str(stream.last_date) if stream.last_date else None,
                    "is_active": stream.is_active,
                })

            for stream in response.outflow_streams:
                all_recurring.append({
                    "type": "outflow",
                    "merchant_name": stream.merchant_name or stream.description,
                    "amount": stream.average_amount.amount if stream.average_amount else None,
                    "frequency": str(stream.frequency.value) if stream.frequency else None,
                    "last_date": str(stream.last_date) if stream.last_date else None,
                    "is_active": stream.is_active,
                })
        except Exception as e:
            all_recurring.append({"error": f"Failed to fetch recurring transactions for {label}: {e}"})

    append_feed_entry(FeedEntry(
        tool_name="get_recurring_transactions",
        params={},
        result_count=len(all_recurring),
    ))
    return all_recurring


@mcp.tool()
def get_holdings() -> list[dict]:
    """Return investment holdings (stocks, funds, etc.) across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_holdings: list[dict] = []

    for label, token in tokens.items():
        try:
            request = InvestmentsHoldingsGetRequest(access_token=token)
            response = client.investments_holdings_get(request)

            securities_map = {s.security_id: s for s in response.securities}

            for holding in response.holdings:
                security = securities_map.get(holding.security_id)
                all_holdings.append({
                    "account_id": holding.account_id,
                    "security_name": security.name if security else None,
                    "ticker": security.ticker_symbol if security else None,
                    "quantity": holding.quantity,
                    "current_value": holding.institution_value,
                    "cost_basis": holding.cost_basis,
                    "currency": holding.iso_currency_code or "USD",
                })
        except Exception as e:
            all_holdings.append({"error": f"Failed to fetch holdings for {label}: {e}"})

    append_feed_entry(FeedEntry(
        tool_name="get_holdings",
        params={},
        result_count=len(all_holdings),
    ))
    return all_holdings


@mcp.tool()
def get_liabilities() -> list[dict]:
    """Return liabilities (credit cards, student loans, mortgages) across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_liabilities: list[dict] = []

    for label, token in tokens.items():
        try:
            request = LiabilitiesGetRequest(access_token=token)
            response = client.liabilities_get(request)
            liabilities = response.liabilities

            if liabilities.credit:
                for card in liabilities.credit:
                    all_liabilities.append({
                        "type": "credit_card",
                        "account_id": card.account_id,
                        "last_payment_amount": card.last_payment_amount,
                        "last_payment_date": str(card.last_payment_date) if card.last_payment_date else None,
                        "minimum_payment_amount": card.minimum_payment_amount,
                        "next_payment_due_date": str(card.next_payment_due_date) if card.next_payment_due_date else None,
                        "is_overdue": card.is_overdue,
                    })

            if liabilities.student:
                for loan in liabilities.student:
                    all_liabilities.append({
                        "type": "student_loan",
                        "account_id": loan.account_id,
                        "loan_name": loan.loan_name,
                        "interest_rate": loan.interest_rate_percentage,
                        "outstanding_balance": loan.outstanding_interest_amount,
                        "last_payment_amount": loan.last_payment_amount,
                        "last_payment_date": str(loan.last_payment_date) if loan.last_payment_date else None,
                        "next_payment_due_date": str(loan.next_payment_due_date) if loan.next_payment_due_date else None,
                        "is_overdue": loan.is_overdue,
                    })

            if liabilities.mortgage:
                for mortgage in liabilities.mortgage:
                    all_liabilities.append({
                        "type": "mortgage",
                        "account_id": mortgage.account_id,
                        "interest_rate": mortgage.interest_rate.percentage if mortgage.interest_rate else None,
                        "interest_rate_type": str(mortgage.interest_rate.type) if mortgage.interest_rate else None,
                        "loan_term": mortgage.loan_term,
                        "maturity_date": str(mortgage.maturity_date) if mortgage.maturity_date else None,
                        "last_payment_amount": mortgage.last_payment_amount,
                        "last_payment_date": str(mortgage.last_payment_date) if mortgage.last_payment_date else None,
                        "next_payment_due_date": str(mortgage.next_payment_due_date) if mortgage.next_payment_due_date else None,
                    })
        except Exception as e:
            all_liabilities.append({"error": f"Failed to fetch liabilities for {label}: {e}"})

    append_feed_entry(FeedEntry(
        tool_name="get_liabilities",
        params={},
        result_count=len(all_liabilities),
    ))
    return all_liabilities


if __name__ == "__main__":
    mcp.run()
