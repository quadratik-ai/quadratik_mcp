# Quadratik MCP Server

Search and manage **220M+ B2B contacts** from the [Quadratik](https://quadratik.com) database directly inside Claude, Cursor, and any other MCP-compatible AI client.

## What you can do

| Tool | Description |
|---|---|
| `search_contacts` | Filter contacts by title, seniority, industry, location, company, email status, and more |
| `save_contacts` | Save contacts to your account (and optionally to a list) |
| `export_contacts` | Export saved contacts as CSV |
| `get_contact_lists` | List all your saved contact lists |
| `create_list` | Create a new contact list |
| `delete_list` | Delete a contact list |
| `get_company_suggestions` | Autocomplete company names |
| `get_industry_suggestions` | Get all industry categories with IDs |
| `get_user_data` | View your account details and usage stats |

> **Note:** `search_contacts` works without an API key but returns masked emails and phone numbers. All write operations and full contact data require a valid API key.

---

## Prerequisites

- Python 3.10+
- A running Quadratik backend **or** a Quadratik API key (for cloud access)

Get your API key at [quadratik.com](https://quadratik.com) → Account Settings → API Keys.

---

## Installation

```bash
cd mcp_server
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

---

## Configuration

The server reads two environment variables:

| Variable | Default | Description |
|---|---|---|
| `QUADRATIK_BACKEND_URL` | `http://localhost:8080` | URL of the Quadratik backend |
| `QUADRATIK_API_KEY` | _(empty)_ | Your Quadratik API key |

---

## IDE Integration

### Claude Desktop

Add to `~/.config/claude/claude_desktop_config.json` (Mac: `~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "quadratik": {
      "command": "/path/to/mcp_server/venv/bin/python",
      "args": ["/path/to/mcp_server/main.py"],
      "env": {
        "QUADRATIK_BACKEND_URL": "http://localhost:8080",
        "QUADRATIK_API_KEY": "your-api-key-here"
      }
    }
  }
}
```

### Cursor

1. Open **Cursor Settings** → **Features** → **MCP**
2. Click **+ Add New MCP Server**
3. Fill in:
   - **Name:** `Quadratik`
   - **Type:** `stdio`
   - **Command:** `/path/to/mcp_server/venv/bin/python`
   - **Args:** `/path/to/mcp_server/main.py`
4. Set environment variables `QUADRATIK_BACKEND_URL` and `QUADRATIK_API_KEY` in your shell profile or Cursor's env config.

### Smithery

Install via [Smithery](https://smithery.ai) — the server is listed there and handles config automatically.

---

## Tool Reference

### `search_contacts`

```
search_contacts(
    job_titles=["CEO", "VP Sales"],
    seniorities=["C-Level", "Director"],
    industry_ids=[42, 17],
    contact_countries=["United States"],
    company_name_contains=["Acme"],
    employees=[50, 500],           # headcount range
    email_validation_stati=["Valid"],
    search_size=50
)
```

**Returns:** `{ contacts: [...], totalCount: int, saved: bool }`

### `save_contacts`

```
save_contacts(contact_ids=[123, 456], list_id=7)
```

**Returns:** `{ contactsAddedCount: int }`

### `export_contacts`

```
export_contacts(contact_ids=[123, 456])
```

**Returns:** CSV string

### `get_contact_lists` / `create_list` / `delete_list`

```
get_contact_lists()
create_list(name="Q2 Prospects")
delete_list(list_id=7)
```

### `get_company_suggestions`

```
get_company_suggestions(company_name="Acme")
# Returns: { results: [{ id, name_clean, logo_url }, ...] }
```

### `get_industry_suggestions`

```
get_industry_suggestions()
# Returns: { results: [{ id, industry }, ...] }
```

---

## Running locally (Docker)

If you're using the Quadratik monorepo with Docker Compose, the backend is available at `http://backend:8080` from within the container network, or `http://localhost:8080` from your host machine.

```bash
# From the repo root
docker compose up backend

# Then in another terminal
cd mcp_server
QUADRATIK_BACKEND_URL=http://localhost:8080 QUADRATIK_API_KEY=your-key python main.py
```
