## Relevant Files

- `pyproject.toml` - Project metadata, dependencies, and Python version requirement. Single source of truth for the project.
- `uv.lock` - Lockfile for reproducible installs via `uv`.
- `.env.example` - Template with placeholder Plaid credentials (`PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV`) and comments.
- `.env` - Real credentials (gitignored). Stores `PLAID_CLIENT_ID`, `PLAID_SECRET`, `PLAID_ENV`, and `ACCESS_TOKEN_*` values. Can be configured from the dashboard Settings UI.
- `.gitignore` - Ignores `.env`, `feed.json`, `__pycache__`, `.venv`, etc.
- `plaid_utils.py` - Shared utility module: `get_plaid_env()` for environment selection, `get_plaid_client()` for Plaid API init, `load_access_tokens()`, `FeedEntry` dataclass, and feed I/O helpers.
- `mcp_server.py` - MCP server script exposing 6 tools via FastMCP: `get_accounts`, `get_balances`, `get_transactions`, `get_recurring_transactions`, `get_holdings`, `get_liabilities`.
- `dashboard.py` - Flask web server: serves dashboard HTML, Plaid Link endpoints (`/plaid/create-link-token`, `/plaid/exchange-token`), data API routes (`/api/accounts`, `/api/transactions`, `/api/feed`), and settings endpoints (`GET/POST /api/settings`).
- `templates/index.html` - Single-page dashboard: vanilla HTML/CSS/JS with dark theme, three data panels, settings modal for Plaid credentials, setup welcome screen, and manual Refresh button.
- `feed.json` - Shared IPC file (gitignored). MCP server appends log entries; dashboard reads them.
- `start.bat` - Windows convenience script to launch both processes.
- `README.md` - Project documentation with architecture diagram, project structure, setup instructions, API reference, and troubleshooting.
- `LICENSE` - MIT license file.

### Notes

- This is a Python 3.12+ project using `uv` for package management.
- No npm/build step — the dashboard is vanilla HTML/CSS/JS (only external script is Plaid Link's own widget).
- Two independent scripts communicate via a shared `feed.json` file.
- Use `uv run mcp_server.py` and `uv run dashboard.py` to run.
- Plaid environment is configurable via `PLAID_ENV` in `.env` — supports `sandbox`, `development`, and `production`.
- Credentials can be entered from the dashboard Settings UI (no need to manually edit `.env`).
- All functions must have type hints and docstrings.
- Use `pathlib.Path` for file operations, f-strings for formatting, timezone-aware datetimes.

## Instructions for Completing Tasks

**IMPORTANT:** As you complete each task, you must check it off in this markdown file by changing `- [ ]` to `- [x]`. This helps track progress and ensures you don't skip any steps.

Example:
- `- [ ] 1.1 Read file` → `- [x] 1.1 Read file` (after completing)

Update the file after completing each sub-task, not just after completing an entire parent task.

## Tasks

- [x] 0.0 Create feature branch
  - [x] 0.1 Initialize a git repository in the project root (`git init`)
  - [x] 0.2 Create and checkout a new branch for this feature (`git checkout -b feature/plaid-mcp-dashboard`)

- [x] 1.0 Project scaffolding and configuration
  - [x] 1.1 Create `pyproject.toml` with project metadata (name: `plaid-mcp-dashboard`, Python `>=3.12`), and dependencies: `flask`, `fastmcp`, `plaid-python`, `python-dotenv`
  - [x] 1.2 Run `uv lock` to generate the `uv.lock` lockfile
  - [x] 1.3 Create `.gitignore` with entries for `.env`, `feed.json`, `__pycache__/`, `.venv/`, `*.pyc`, `.python-version`
  - [x] 1.4 Create `.env.example` with placeholder values and comments for `PLAID_CLIENT_ID`, `PLAID_SECRET`, and a sample `ACCESS_TOKEN_CHASE` entry
  - [x] 1.5 Create an empty `templates/` directory for the dashboard HTML

- [x] 2.0 Shared Plaid utilities module
  - [x] 2.1 Create `plaid_utils.py` with a function `get_plaid_client()` that returns a configured `plaid.ApiClient` and `plaid.api.PlaidApi` instance using credentials from `.env` (pointing to `production.plaid.com`)
  - [x] 2.2 Add a function `load_access_tokens()` that reads the `.env` file and returns a `dict[str, str]` of all keys matching `ACCESS_TOKEN_*` and their values (e.g. `{"CHASE": "access-sandbox-..."}`)
  - [x] 2.3 Add a dataclass `FeedEntry` with fields: `tool_name: str`, `params: dict`, `result_count: int`, `timestamp: str` — used for `feed.json` log entries
  - [x] 2.4 Add a function `append_feed_entry(entry: FeedEntry)` that reads `feed.json`, appends the new entry, and writes it back (creating the file if it doesn't exist). Use `pathlib.Path` and handle file locking or atomic writes to avoid corruption from concurrent access.

- [x] 3.0 MCP Server (`mcp_server.py`)
  - [x] 3.1 Create `mcp_server.py` with the `#!/usr/bin/env python3` shebang and inline script metadata block for `uv` (specifying dependencies so `uv run mcp_server.py` works)
  - [x] 3.2 On startup, clear `feed.json` (write an empty JSON array `[]`) so the feed resets each session
  - [x] 3.3 Initialize a `FastMCP` server instance with a descriptive name (e.g. `"plaid-finance"`)
  - [x] 3.4 Implement the `get_accounts()` tool — iterates all access tokens, calls Plaid's `/accounts/get` for each, returns a list of dicts with `institution_name`, `account_name`, `account_type`, and `account_id`. Log a `FeedEntry` to `feed.json`.
  - [x] 3.5 Implement the `get_balances()` tool — iterates all access tokens, calls Plaid's `/accounts/balance/get` for each, returns a list of dicts with account name, current balance, available balance, and currency. Log a `FeedEntry` to `feed.json`.
  - [x] 3.6 Implement the `get_transactions(start_date: str, end_date: str)` tool — iterates all access tokens, calls Plaid's `/transactions/get` for each, merges and sorts by date descending, returns a list of dicts with date, merchant name, amount, and category. Dates must be `YYYY-MM-DD` format. Log a `FeedEntry` to `feed.json`.
  - [x] 3.7 Add the `if __name__ == "__main__"` block that runs the MCP server (using `mcp.run()` with stdio transport so LM Studio can connect)

- [x] 4.0 Dashboard server (`dashboard.py`) — backend routes and API
  - [x] 4.1 Create `dashboard.py` with the shebang and inline script metadata block for `uv` (specifying `flask`, `plaid-python`, `python-dotenv` dependencies)
  - [x] 4.2 Initialize the Flask app and load `.env` using `python-dotenv`
  - [x] 4.3 Create route `GET /` that renders `templates/index.html`
  - [x] 4.4 Create route `GET /api/accounts` that loads all access tokens, calls Plaid's `/accounts/balance/get` for each, and returns JSON with account names, balances, and institution names
  - [x] 4.5 Create route `GET /api/transactions` that loads all access tokens, fetches the 20 most recent transactions across all accounts (last 30 days), and returns JSON sorted by date descending with date, merchant name, and amount
  - [x] 4.6 Create route `GET /api/feed` that reads `feed.json` and returns its contents as JSON (return an empty array if the file doesn't exist or is empty)
  - [x] 4.7 Add the `if __name__ == "__main__"` block that runs Flask on `localhost:8080` with `debug=False`

- [x] 5.0 Dashboard frontend — single-page HTML/CSS/JS
  - [x] 5.1 Create `templates/index.html` with the base HTML structure, a `<header>` with the project title and "Connect a Bank" button, and three section containers
  - [x] 5.2 Add CSS styles: dark background (`#1a1a2e` or similar), light text, monospace font for the feed section, card-style containers for each section, clean developer-tool aesthetic
  - [x] 5.3 Build the **Accounts & Balances** section — on page load, fetch `GET /api/accounts` and render each account as a row showing institution name, account name, account type, and current balance
  - [x] 5.4 Build the **Recent Transactions** section — on page load, fetch `GET /api/transactions` and render the 20 most recent as rows showing date, merchant name, and amount
  - [x] 5.5 Build the **MCP Activity Feed** section — fetch `GET /api/feed` on load and on manual refresh, render entries in the format `[HH:MM:SS] tool_name(params) → N results`, newest at top, monospace font
  - [x] 5.6 Add a "no accounts linked" prompt state — if `/api/accounts` returns an empty list, display a message prompting the user to click "Connect a Bank"
  - [x] 5.7 Ensure the page has no external dependencies — no CDN links, no npm, no build step. All CSS and JS must be inline or in `<style>`/`<script>` tags within the HTML file.

- [x] 6.0 Plaid Link flow (bank account linking end-to-end)
  - [x] 6.1 Add route `POST /plaid/create-link-token` in `dashboard.py` — calls Plaid's `/link/token/create` with `products=["transactions"]`, `country_codes=["US"]`, `language="en"`, and a user client ID. Returns the `link_token` as JSON.
  - [x] 6.2 Add route `POST /plaid/exchange-token` in `dashboard.py` — receives `{ "public_token": "...", "institution_name": "..." }` from the frontend, calls Plaid's `/item/public_token/exchange` to get the permanent `access_token`
  - [x] 6.3 In the exchange endpoint, sanitize the institution name (uppercase, replace spaces with underscores) and append the new token to `.env` as `ACCESS_TOKEN_<INSTITUTION_NAME>=<access_token>`
  - [x] 6.4 After appending to `.env`, reload the environment variables in the running process (using `dotenv.load_dotenv(override=True)`) so the dashboard reflects the new account without a restart
  - [x] 6.5 In `templates/index.html`, add JavaScript for the "Connect a Bank" button: fetch `/plaid/create-link-token`, initialize the Plaid Link handler using the `link_token`, and on success send the `public_token` and `institution.name` to `/plaid/exchange-token`
  - [x] 6.6 After successful token exchange, refresh the Accounts & Balances and Recent Transactions sections on the page without a full page reload
  - [x] 6.7 Include the Plaid Link `<script>` tag (`https://cdn.plaid.com/link/v2/stable/link-initialize.js`) — this is the one required external script for Plaid's own widget

- [x] 7.0 Documentation and repo polish
  - [x] 7.1 Create `README.md` with: project title, one-line description, and an ASCII architecture diagram showing `Browser ↔ dashboard.py ↔ Plaid API`, `LM Studio ↔ mcp_server.py ↔ Plaid API`, and `mcp_server.py → feed.json → dashboard.py`
  - [x] 7.2 Add Prerequisites section listing `uv`, Plaid developer account, and LM Studio with a tool-calling model
  - [x] 7.3 Add Setup Instructions section with the numbered steps: clone, copy `.env.example` to `.env`, fill in credentials, run both scripts, open browser, connect a bank, configure LM Studio
  - [x] 7.4 Add Available MCP Tools table with columns: Tool, Parameters, Returns — listing `get_accounts`, `get_balances`, and `get_transactions`
  - [x] 7.5 Add Troubleshooting section covering: Plaid token errors, LM Studio not connecting to MCP, dashboard not showing new accounts
  - [x] 7.6 Add a "How to link additional banks" paragraph explaining the "Connect a Bank" button
  - [x] 7.7 Create `LICENSE` file with the MIT license text
  - [x] 7.8 Create `start.bat` convenience script that launches `uv run mcp_server.py` and `uv run dashboard.py` in separate terminal windows
  - [x] 7.9 Final review: ensure no commented-out code, all functions have docstrings and type hints, `.env` and `feed.json` are in `.gitignore`, and the project runs end-to-end with `uv run`
