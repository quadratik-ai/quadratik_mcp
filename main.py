import json
import os
import contextvars
from urllib.parse import parse_qs
from typing import List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from starlette.types import ASGIApp, Receive, Scope, Send

# ---------------------------------------------------------------------------
# Per-request config (populated by _ConfigMiddleware for HTTP transport,
# or from env vars for stdio transport)
# ---------------------------------------------------------------------------

_DEFAULT_BACKEND = os.environ.get("QUADRATIK_BACKEND_URL", "https://api.quadratik.ai")
_DEFAULT_API_KEY = os.environ.get("QUADRATIK_API_KEY", "")

_backend_url: contextvars.ContextVar[str] = contextvars.ContextVar("backend_url", default=_DEFAULT_BACKEND)
_api_key: contextvars.ContextVar[str] = contextvars.ContextVar("api_key", default=_DEFAULT_API_KEY)


class _ConfigMiddleware:
    """Injects backendUrl and apiKey query params into context vars per request.
    Also serves a /health endpoint for deployment health checks."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("path") == "/health":
            body = b'{"status":"ok"}'
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({"type": "http.response.body", "body": body})
            return

        if scope["type"] == "http" and scope.get("path") == "/.well-known/mcp/server-card.json":
            card = json.dumps({
                "serverInfo": {
                    "name": "Quadratik",
                    "version": "1.0.0",
                },
                "authentication": {
                    "required": False,
                },
                "tools": [
                    {
                        "name": "search_contacts",
                        "description": "Search the Quadratik B2B contact database with rich filters. Returns contacts matching criteria like job title, company, location, industry, seniority, and more.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "job_titles": {"type": "array", "items": {"type": "string"}},
                                "seniorities": {"type": "array", "items": {"type": "string"}},
                                "contact_countries": {"type": "array", "items": {"type": "string"}},
                                "company_name_contains": {"type": "array", "items": {"type": "string"}},
                                "search_size": {"type": "integer", "default": 25},
                            },
                        },
                    },
                    {"name": "save_contacts", "description": "Save contacts to your Quadratik account.", "inputSchema": {"type": "object", "properties": {"contact_ids": {"type": "array", "items": {"type": "integer"}}}, "required": ["contact_ids"]}},
                    {"name": "export_contacts", "description": "Export saved contacts as CSV.", "inputSchema": {"type": "object", "properties": {"contact_ids": {"type": "array", "items": {"type": "integer"}}}, "required": ["contact_ids"]}},
                    {"name": "get_contact_lists", "description": "Retrieve all saved contact lists.", "inputSchema": {"type": "object", "properties": {}}},
                    {"name": "create_list", "description": "Create a new contact list.", "inputSchema": {"type": "object", "properties": {"name": {"type": "string"}}, "required": ["name"]}},
                    {"name": "delete_list", "description": "Delete a contact list.", "inputSchema": {"type": "object", "properties": {"list_id": {"type": "integer"}}, "required": ["list_id"]}},
                    {"name": "get_company_suggestions", "description": "Autocomplete company names.", "inputSchema": {"type": "object", "properties": {"company_name": {"type": "string"}}, "required": ["company_name"]}},
                    {"name": "get_industry_suggestions", "description": "Retrieve all industry categories.", "inputSchema": {"type": "object", "properties": {}}},
                    {"name": "get_user_data", "description": "Fetch your Quadratik account data.", "inputSchema": {"type": "object", "properties": {}}},
                ],
                "resources": [],
                "prompts": [],
            }).encode()
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [[b"content-type", b"application/json"]],
            })
            await send({"type": "http.response.body", "body": card})
            return

        if scope["type"] in ("http", "websocket"):
            params = parse_qs(scope.get("query_string", b"").decode())
            # API key: check X-API-Key header first, then query param, then env default
            headers_list = scope.get("headers", [])
            header_api_key = ""
            for hdr_name, hdr_value in headers_list:
                if hdr_name == b"x-api-key":
                    header_api_key = hdr_value.decode()
                    break
            api_key = header_api_key or params.get("apiKey", [_DEFAULT_API_KEY])[0]
            t1 = _backend_url.set(params.get("backendUrl", [_DEFAULT_BACKEND])[0])
            t2 = _api_key.set(api_key)
            try:
                await self.app(scope, receive, send)
            finally:
                _backend_url.reset(t1)
                _api_key.reset(t2)
        else:
            await self.app(scope, receive, send)


mcp = FastMCP("Quadratik", streamable_http_path="/")


def _headers() -> dict:
    key = _api_key.get()
    return {"Authorization": f"Bearer {key}"} if key else {}


# ---------------------------------------------------------------------------
# Contacts
# ---------------------------------------------------------------------------

@mcp.tool()
async def search_contacts(
    job_titles: Optional[List[str]] = None,
    seniorities: Optional[List[str]] = None,
    industry_ids: Optional[List[int]] = None,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    contact_cities: Optional[List[str]] = None,
    contact_states: Optional[List[str]] = None,
    contact_countries: Optional[List[str]] = None,
    company_name_contains: Optional[List[str]] = None,
    company_cities: Optional[List[str]] = None,
    company_states: Optional[List[str]] = None,
    company_countries: Optional[List[str]] = None,
    company_website_urls: Optional[List[str]] = None,
    email_validation_stati: Optional[List[str]] = None,
    phone_types: Optional[List[str]] = None,
    employees: Optional[List[Optional[int]]] = None,
    revenue: Optional[List[Optional[int]]] = None,
    funding: Optional[List[Optional[int]]] = None,
    founded: Optional[List[Optional[int]]] = None,
    search_size: int = 25,
) -> dict:
    """Search the Quadratik B2B contact database with rich filters.

    Returns a list of contacts matching the given criteria. Sensitive fields
    (email, phone) are masked unless authenticated with a valid API key.

    Args:
        job_titles: Filter by job titles, e.g. ["CEO", "VP Sales"]. Acronyms
            like "CTO" are automatically expanded.
        seniorities: Filter by seniority levels, e.g. ["C-Level", "Director"].
        industry_ids: Filter by industry IDs (get IDs from get_industry_suggestions).
        first_name: Filter by exact first name (case-insensitive).
        last_name: Filter by exact last name (case-insensitive).
        contact_cities: Filter by contact's city, e.g. ["New York", "London"].
        contact_states: Filter by contact's state/province.
        contact_countries: Filter by contact's country.
        company_name_contains: Filter by partial company name match.
        company_cities: Filter by company headquarters city.
        company_states: Filter by company headquarters state/province.
        company_countries: Filter by company headquarters country.
        company_website_urls: Filter by exact company website URLs.
        email_validation_stati: Filter by email status: "Valid", "Catch All",
            "Invalid", or "Any Status".
        phone_types: Filter contacts with phone numbers: "mobile", "company".
        employees: Headcount range as [min, max]. Use null for open-ended,
            e.g. [50, 500] or [1000, null].
        revenue: Annual revenue range as [min, max] in USD.
        funding: Total funding range as [min, max] in USD.
        founded: Founded year range as [min, max], e.g. [2010, 2020].
        search_size: Maximum number of results to return (default 25, max 2500).
    """
    payload = {
        "searchSize": search_size,
        "jobTitles": job_titles or [],
        "seniorities": seniorities,
        "industryIds": industry_ids or [],
        "firstName": first_name,
        "lastName": last_name,
        "contactCities": contact_cities or [],
        "contactStates": contact_states or [],
        "contactCountries": contact_countries or [],
        "companyNameContains": company_name_contains or [],
        "companyCities": company_cities or [],
        "companyStates": company_states or [],
        "companyCountries": company_countries or [],
        "companyWebsiteUrls": company_website_urls or [],
        "emailValidationStati": email_validation_stati or [],
        "phoneTypes": phone_types or [],
        "employees": employees,
        "revenue": revenue,
        "funding": funding,
        "founded": founded,
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/search",
            json=payload,
            headers=_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def save_contacts(
    contact_ids: List[int],
    list_id: Optional[int] = None,
) -> dict:
    """Save contacts to your Quadratik account (and optionally to a list).

    Requires a valid API key set via QUADRATIK_API_KEY.

    Args:
        contact_ids: List of contact IDs to save (from search_contacts results).
        list_id: Optional list ID to also add the contacts to. Get list IDs
            from get_contact_lists.
    """
    payload: dict = {"contactIds": contact_ids}
    if list_id is not None:
        payload["list_id"] = list_id
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/save_contacts",
            json=payload,
            headers=_headers(),
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def export_contacts(contact_ids: List[int]) -> str:
    """Export saved contacts as a CSV string.

    Only contacts that have been previously saved to your account can be
    exported. Requires a valid API key set via QUADRATIK_API_KEY.

    Args:
        contact_ids: List of saved contact IDs to export.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/export",
            json={"contactIds": contact_ids},
            headers=_headers(),
            timeout=60.0,
        )
        response.raise_for_status()
        return response.text


# ---------------------------------------------------------------------------
# Contact lists
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_contact_lists() -> dict:
    """Retrieve all saved contact lists for your Quadratik account.

    Requires a valid API key set via QUADRATIK_API_KEY.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_backend_url.get()}/saved_contact_lists",
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def create_list(name: str) -> dict:
    """Create a new contact list in your Quadratik account.

    Requires a valid API key set via QUADRATIK_API_KEY.

    Args:
        name: The name for the new list (must be unique within your account).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/create_list",
            json={"name": name},
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def delete_list(list_id: int) -> dict:
    """Delete a contact list from your Quadratik account.

    This removes the list and its memberships but does NOT delete the saved
    contacts themselves. Requires a valid API key set via QUADRATIK_API_KEY.

    Args:
        list_id: The ID of the list to delete (from get_contact_lists).
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/delete_list",
            json={"list_id": list_id},
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Lookup / autocomplete
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_company_suggestions(company_name: str) -> dict:
    """Autocomplete company names in the Quadratik database.

    Returns up to 5 matching companies with their IDs and logos. Use the
    returned company IDs with search_contacts to filter by specific companies.

    Args:
        company_name: Partial or full company name to search for.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/get_company_suggestions",
            json={"companyName": company_name},
            headers=_headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


@mcp.tool()
async def get_industry_suggestions() -> dict:
    """Retrieve all industry categories available in the Quadratik database.

    Returns a list of industries with their IDs and names. Pass the IDs to
    search_contacts via the industry_ids parameter to filter by industry.
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{_backend_url.get()}/get_industry_suggestions",
            headers=_headers(),
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Account
# ---------------------------------------------------------------------------

@mcp.tool()
async def get_user_data() -> dict:
    """Fetch your Quadratik account data including plan details and usage stats.

    Requires a valid API key set via QUADRATIK_API_KEY.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{_backend_url.get()}/fetch_user_data",
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    print(f"Starting Quadratik MCP server...", flush=True)
    transport = os.environ.get("MCP_TRANSPORT", "stdio")
    print(f"Transport: {transport}", flush=True)
    if transport == "http":
        import uvicorn
        port = int(os.environ.get("PORT", "8000"))
        print(f"Listening on 0.0.0.0:{port}", flush=True)
        base_app = mcp.streamable_http_app()
        uvicorn.run(
            _ConfigMiddleware(base_app),
            host="0.0.0.0",
            port=port,
        )
    else:
        mcp.run(transport="stdio")
