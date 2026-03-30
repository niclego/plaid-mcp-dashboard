# Plaid MCP Dashboard

A local, private personal finance tool that lets you chat with your bank data via LM Studio while viewing accounts, transactions, and AI activity in a browser dashboard.

<img width="2559" height="1389" alt="Screenshot 2026-03-29 201926" src="https://github.com/user-attachments/assets/4f34f828-69b5-4593-b8b0-0b88af600c25" />

## Disclaimer

This is 100% vibe coded.

## Architecture

```
┌─────────────┐    stdio     ┌──────────────────┐    HTTPS    ┌───────────┐
│  LM Studio  │◄────────────►│  mcp_server.py   │◄───────────►│ Plaid API │
│  (local LLM)│              │  (MCP tools)     │             └───────────┘
└─────────────┘              └────────┬─────────┘                   ▲
                                      │ writes                     │
                                      ▼                            │ HTTPS
                               ┌────────────┐                     │
                               │ feed.json  │                     │
                               └──────┬─────┘                     │
                                      │ reads                     │
                                      ▼                            │
┌─────────────┐    HTTP      ┌──────────────────┐                 │
│   Browser   │◄────────────►│  dashboard.py    │◄────────────────┘
│ :8080       │              │  (Flask server)  │
└─────────────┘              └──────────────────┘
```

**Key components:**

- **mcp_server.py** — MCP server exposing Plaid data as tools for LM Studio
- **dashboard.py** — Flask web server at `localhost:8080` with accounts, transactions, activity feed, and settings
- **plaid_utils.py** — Shared module used by both scripts for Plaid client setup, token loading, and feed logging
- **feed.json** — shared file for inter-process communication (MCP server writes, dashboard reads)

## Prerequisites

- **[uv](https://docs.astral.sh/uv/)** — Python package manager (handles venv and deps automatically)
- **Plaid developer account** — get your `client_id` and `secret` from [dashboard.plaid.com](https://dashboard.plaid.com/developers/keys)
- **LM Studio** — installed with a tool-calling capable model loaded (e.g. Qwen, Llama 3)

## Setup

1. **Clone the repo**
   ```bash
   git clone https://github.com/YOUR_USERNAME/plaid-mcp-dashboard.git
   cd plaid-mcp-dashboard
   ```

2. **Start the MCP server** (Terminal 1)
   ```bash
   uv run mcp_server.py
   ```

3. **Start the dashboard** (Terminal 2)
   ```bash
   uv run dashboard.py
   ```

4. **Open the dashboard** — navigate to [http://localhost:8080](http://localhost:8080)

5. **Configure credentials** — the dashboard will show a welcome screen on first launch. Click **Settings** and enter your `PLAID_CLIENT_ID`, `PLAID_SECRET`, and choose your Plaid environment:
   - **Sandbox** — fake test data, no real bank needed (good for initial testing)
   - **Production** — real banks with full access

   Alternatively, you can configure manually by copying `.env.example` to `.env` and editing it directly.

6. **Connect a bank** — click **"Connect a Bank"** and follow the Plaid Link flow

7. **Configure LM Studio** — add the MCP server in LM Studio's settings:
   - **Transport:** stdio
   - **Command:** `uv run mcp_server.py`
   - **Working directory:** the project root

> **Windows shortcut:** Run `start.bat` to launch both servers in separate terminal windows automatically.

## Linking Additional Banks

Click the **"Connect a Bank"** button in the dashboard header at any time. Each linked bank adds a new `ACCESS_TOKEN_*` entry to your `.env` file automatically. The dashboard updates immediately — no restart needed.

## Available MCP Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_accounts` | *(none)* | List of all linked accounts with institution name, account name, and type |
| `get_balances` | *(none)* | Current and available balances for every linked account |
| `get_transactions` | `start_date` (YYYY-MM-DD), `end_date` (YYYY-MM-DD) | Merged, date-sorted transactions across all accounts with merchant name, amount, and category |
| `get_recurring_transactions` | *(none)* | Auto-detected recurring charges and subscriptions (merchant, amount, frequency, active status) |
| `get_holdings` | *(none)* | Investment holdings across all accounts (security name, ticker, quantity, current value, cost basis) |
| `get_liabilities` | *(none)* | Credit cards, student loans, and mortgages with payment info, interest rates, and due dates |

## Dashboard API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Serves the dashboard HTML page |
| `/api/accounts` | GET | Returns all linked accounts with balances |
| `/api/transactions` | GET | Returns the 20 most recent transactions |
| `/api/feed` | GET | Returns the MCP activity feed from `feed.json` |
| `/api/settings` | GET | Returns current config status (credentials set, environment) |
| `/api/settings` | POST | Saves Plaid credentials and environment to `.env` |
| `/plaid/create-link-token` | POST | Creates a Plaid Link token for bank linking |
| `/plaid/exchange-token` | POST | Exchanges a public token for a permanent access token |

## Troubleshooting

**Plaid token errors**
- Verify your `PLAID_CLIENT_ID` and `PLAID_SECRET` are correct — you can check and update them from the **Settings** button in the dashboard
- Ensure your credentials match the `PLAID_ENV` setting — sandbox keys won't work with production and vice versa
- If a bank requires re-authentication, re-link it via the "Connect a Bank" button

**LM Studio not connecting to MCP server**
- Make sure `mcp_server.py` is running in a separate terminal before configuring LM Studio
- In LM Studio, set the transport to **stdio** and the command to `uv run mcp_server.py`
- Ensure the working directory points to this project's root folder

**Dashboard not showing new accounts after linking**
- Click the **Refresh** button in the dashboard header to reload data — or refresh the page
- Check that the new `ACCESS_TOKEN_*` entry was added to `.env`
- Restart `dashboard.py` if the `.env` changes aren't being picked up

**Dashboard shows "Welcome" screen even after configuring**
- Ensure you clicked **Save** in the Settings modal and saw the success message
- Check that a `.env` file was created in the project root with your credentials

## Project Structure

```
plaid-mcp-dashboard/
├── mcp_server.py        # MCP server — run in Terminal 1
├── dashboard.py         # Flask dashboard — run in Terminal 2
├── plaid_utils.py       # Shared Plaid client, token loading, feed helpers
├── templates/
│   └── index.html       # Dashboard UI (vanilla HTML/CSS/JS)
├── pyproject.toml       # Project config and dependencies
├── uv.lock              # Reproducible dependency lockfile
├── .env.example         # Credential template
├── .gitignore           # Excludes .env, feed.json, __pycache__, etc.
├── start.bat            # Windows convenience launcher
├── LICENSE              # MIT
└── README.md
```

## License

MIT
