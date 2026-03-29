# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask>=3.0",
#     "plaid-python>=29.0",
#     "python-dotenv>=1.0",
# ]
# ///
"""Flask dashboard server for the Plaid MCP finance tool."""

import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from plaid.model.accounts_balance_get_request import AccountsBalanceGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.institutions_get_by_id_request import InstitutionsGetByIdRequest
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.investments_holdings_get_request import InvestmentsHoldingsGetRequest
from plaid.model.liabilities_get_request import LiabilitiesGetRequest
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_recurring_get_request import TransactionsRecurringGetRequest

from plaid_utils import get_plaid_client, load_access_tokens

load_dotenv(override=True)

app = Flask(__name__)

FEED_PATH = Path(__file__).parent / "feed.json"
ENV_PATH = Path(__file__).parent / ".env"


@app.route("/")
def index() -> str:
    """Serve the main dashboard page."""
    return render_template("index.html")


@app.route("/api/accounts")
def api_accounts() -> tuple:
    """Return all linked accounts with balances and institution names."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    accounts: list[dict] = []

    for label, token in tokens.items():
        try:
            request_obj = AccountsBalanceGetRequest(access_token=token)
            response = client.accounts_balance_get(request_obj)
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
                balance = account.balances
                accounts.append({
                    "institution_name": institution_name,
                    "account_name": account.name,
                    "account_type": str(account.type.value),
                    "current_balance": balance.current,
                    "available_balance": balance.available,
                    "currency": balance.iso_currency_code or "USD",
                })
        except Exception as e:
            accounts.append({"error": f"Failed to fetch accounts for {label}: {e}"})

    return jsonify(accounts), 200


@app.route("/api/transactions")
def api_transactions() -> tuple:
    """Return the 20 most recent transactions across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_transactions: list[dict] = []

    end_date = datetime.now(UTC).date()
    start_date = end_date - timedelta(days=30)

    for label, token in tokens.items():
        try:
            request_obj = TransactionsGetRequest(
                access_token=token,
                start_date=start_date,
                end_date=end_date,
            )
            response = client.transactions_get(request_obj)

            for txn in response.transactions:
                all_transactions.append({
                    "date": str(txn.date),
                    "merchant_name": txn.merchant_name or txn.name,
                    "amount": txn.amount,
                })
        except Exception as e:
            all_transactions.append({"error": f"Failed to fetch transactions for {label}: {e}"})

    all_transactions.sort(key=lambda t: t.get("date", ""), reverse=True)
    return jsonify(all_transactions[:20]), 200


@app.route("/api/recurring")
def api_recurring() -> tuple:
    """Return recurring transactions (subscriptions, bills) across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_recurring: list[dict] = []

    for label, token in tokens.items():
        try:
            request_obj = TransactionsRecurringGetRequest(access_token=token)
            response = client.transactions_recurring_get(request_obj)

            for stream in response.outflow_streams:
                all_recurring.append({
                    "merchant_name": stream.merchant_name or stream.description,
                    "amount": stream.average_amount.amount if stream.average_amount else None,
                    "frequency": str(stream.frequency.value) if stream.frequency else None,
                    "last_date": str(stream.last_date) if stream.last_date else None,
                    "is_active": stream.is_active,
                })
        except Exception as e:
            all_recurring.append({"error": f"Failed to fetch recurring for {label}: {e}"})

    return jsonify(all_recurring), 200


@app.route("/api/investments")
def api_investments() -> tuple:
    """Return investment holdings across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_holdings: list[dict] = []

    for label, token in tokens.items():
        try:
            request_obj = InvestmentsHoldingsGetRequest(access_token=token)
            response = client.investments_holdings_get(request_obj)
            securities_map = {s.security_id: s for s in response.securities}

            for holding in response.holdings:
                security = securities_map.get(holding.security_id)
                all_holdings.append({
                    "security_name": security.name if security else None,
                    "ticker": security.ticker_symbol if security else None,
                    "quantity": holding.quantity,
                    "current_value": holding.institution_value,
                    "cost_basis": holding.cost_basis,
                    "currency": holding.iso_currency_code or "USD",
                })
        except Exception as e:
            all_holdings.append({"error": f"Failed to fetch investments for {label}: {e}"})

    return jsonify(all_holdings), 200


@app.route("/api/liabilities")
def api_liabilities() -> tuple:
    """Return liabilities (credit cards, student loans, mortgages) across all linked accounts."""
    client = get_plaid_client()
    tokens = load_access_tokens()
    all_liabilities: list[dict] = []

    for label, token in tokens.items():
        try:
            request_obj = LiabilitiesGetRequest(access_token=token)
            response = client.liabilities_get(request_obj)
            liabilities = response.liabilities

            if liabilities.credit:
                for card in liabilities.credit:
                    all_liabilities.append({
                        "type": "Credit Card",
                        "account_id": card.account_id,
                        "last_payment_amount": card.last_payment_amount,
                        "minimum_payment": card.minimum_payment_amount,
                        "next_due_date": str(card.next_payment_due_date) if card.next_payment_due_date else None,
                        "is_overdue": card.is_overdue,
                    })

            if liabilities.student:
                for loan in liabilities.student:
                    all_liabilities.append({
                        "type": "Student Loan",
                        "account_id": loan.account_id,
                        "loan_name": loan.loan_name,
                        "interest_rate": loan.interest_rate_percentage,
                        "last_payment_amount": loan.last_payment_amount,
                        "next_due_date": str(loan.next_payment_due_date) if loan.next_payment_due_date else None,
                        "is_overdue": loan.is_overdue,
                    })

            if liabilities.mortgage:
                for mortgage in liabilities.mortgage:
                    all_liabilities.append({
                        "type": "Mortgage",
                        "account_id": mortgage.account_id,
                        "interest_rate": mortgage.interest_rate.percentage if mortgage.interest_rate else None,
                        "loan_term": mortgage.loan_term,
                        "last_payment_amount": mortgage.last_payment_amount,
                        "next_due_date": str(mortgage.next_payment_due_date) if mortgage.next_payment_due_date else None,
                    })
        except Exception as e:
            all_liabilities.append({"error": f"Failed to fetch liabilities for {label}: {e}"})

    return jsonify(all_liabilities), 200


@app.route("/api/feed")
def api_feed() -> tuple:
    """Return the contents of feed.json (the MCP activity log)."""
    if not FEED_PATH.exists():
        return jsonify([]), 200
    try:
        entries = json.loads(FEED_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, ValueError):
        entries = []
    return jsonify(entries), 200


@app.route("/api/feed/clear", methods=["POST"])
def clear_feed() -> tuple:
    """Clear the MCP activity feed."""
    FEED_PATH.write_text("[]", encoding="utf-8")
    return jsonify({"status": "ok"}), 200


@app.route("/api/settings")
def api_settings() -> tuple:
    """Return current Plaid configuration status (without exposing secrets)."""
    load_dotenv(override=True)
    client_id = os.environ.get("PLAID_CLIENT_ID", "")
    secret = os.environ.get("PLAID_SECRET", "")
    plaid_env = os.environ.get("PLAID_ENV", "sandbox")
    return jsonify({
        "has_client_id": bool(client_id and client_id != "your_client_id_here"),
        "has_secret": bool(secret and secret != "your_secret_here"),
        "plaid_env": plaid_env,
        "client_id_preview": f"{client_id[:4]}...{client_id[-4:]}" if len(client_id) > 8 else "",
    }), 200


@app.route("/api/settings", methods=["POST"])
def save_settings() -> tuple:
    """Save Plaid credentials and environment to .env."""
    data = request.get_json()
    client_id: str = data.get("client_id", "").strip()
    secret: str = data.get("secret", "").strip()
    plaid_env: str = data.get("plaid_env", "sandbox").strip().lower()

    if plaid_env not in ("sandbox", "production"):
        return jsonify({"error": "Invalid PLAID_ENV"}), 400

    env_lines: dict[str, str] = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and "=" in stripped:
                key, _, value = stripped.partition("=")
                env_lines[key.strip()] = value.strip()

    if client_id:
        env_lines["PLAID_CLIENT_ID"] = client_id
    if secret:
        env_lines["PLAID_SECRET"] = secret
    env_lines["PLAID_ENV"] = plaid_env

    content = "# Plaid MCP Dashboard configuration\n"
    for key, value in env_lines.items():
        content += f"{key}={value}\n"
    ENV_PATH.write_text(content, encoding="utf-8")

    load_dotenv(override=True)
    os.environ["PLAID_CLIENT_ID"] = env_lines.get("PLAID_CLIENT_ID", "")
    os.environ["PLAID_SECRET"] = env_lines.get("PLAID_SECRET", "")
    os.environ["PLAID_ENV"] = plaid_env

    return jsonify({"status": "ok"}), 200


@app.route("/plaid/create-link-token", methods=["POST"])
def create_link_token() -> tuple:
    """Create a Plaid Link token for the frontend to initialize Plaid Link."""
    client = get_plaid_client()
    request_obj = LinkTokenCreateRequest(
        user=LinkTokenCreateRequestUser(client_user_id="local-user"),
        client_name="Plaid MCP Dashboard",
        products=[Products("transactions"), Products("investments"), Products("liabilities")],
        country_codes=[CountryCode("US")],
        language="en",
    )
    response = client.link_token_create(request_obj)
    return jsonify({"link_token": response.link_token}), 200


@app.route("/plaid/exchange-token", methods=["POST"])
def exchange_token() -> tuple:
    """Exchange a Plaid public_token for a permanent access_token and save it to .env."""
    data = request.get_json()
    public_token: str = data["public_token"]
    institution_name: str = data.get("institution_name", "BANK")

    client = get_plaid_client()
    exchange_request = ItemPublicTokenExchangeRequest(public_token=public_token)
    response = client.item_public_token_exchange(exchange_request)
    access_token = response.access_token

    sanitized_name = re.sub(r"[^A-Z0-9]", "_", institution_name.upper()).strip("_")
    env_key = f"ACCESS_TOKEN_{sanitized_name}"

    with ENV_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n{env_key}={access_token}\n")

    os.environ[env_key] = access_token
    load_dotenv(override=True)

    return jsonify({"status": "ok", "key": env_key}), 200


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8080, debug=False)
