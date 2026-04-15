import os
from typing import List, Optional
import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Quadratik")

BACKEND_URL = os.environ.get("QUADRATIK_BACKEND_URL", "http://localhost:8080")
API_KEY = os.environ.get("QUADRATIK_API_KEY", "")


def _headers() -> dict:
    if API_KEY:
        return {"Authorization": f"Bearer {API_KEY}"}
    return {}


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
            f"{BACKEND_URL}/search",
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
            f"{BACKEND_URL}/save_contacts",
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
            f"{BACKEND_URL}/export",
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
            f"{BACKEND_URL}/saved_contact_lists",
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
            f"{BACKEND_URL}/create_list",
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
            f"{BACKEND_URL}/delete_list",
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
            f"{BACKEND_URL}/get_company_suggestions",
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
            f"{BACKEND_URL}/get_industry_suggestions",
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
            f"{BACKEND_URL}/fetch_user_data",
            headers=_headers(),
            timeout=15.0,
        )
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")
