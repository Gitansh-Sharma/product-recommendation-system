"""
api_client.py
-------------
Module 1: API Client
 
Responsibility:
    This is the ONLY module in the whole project that is allowed to make
    outbound HTTP calls. Every other module (filters, recommender, GUI)
    asks THIS module for data instead of calling `requests` directly.
 
Design decision (important for project report / viva):
    Centralizing network access in one module means:
      1. If we swap FakeStore/DummyJSON for a different API later,
         only this file changes.
      2. Error handling (timeouts, bad status codes, malformed JSON)
         is written ONCE and reused everywhere, instead of being
         duplicated in every GUI screen.
      3. It matches the "Project Architecture" diagram in the MVP doc,
         where "API Manager" sits as its own box between the
         Recommendation Engine and the raw REST APIs.
 
Every public function in this file returns a Python dict in the shape:
 
    {
        "success": True/False,
        "data": <parsed JSON or None>,
        "error": <human-readable message or None>
    }
 
This lets the GUI layer always check `result["success"]` first and show
the "Unable to connect. Please try again later." message (Module 11 —
Error Handling) without needing to know *why* it failed.
"""
 
import time
import requests
 
from api.endpoints import (
    FAKESTORE_ENDPOINTS,
    DUMMYJSON_ENDPOINTS,
    REQUEST_TIMEOUT_SECONDS,
    MAX_RETRIES,
)
 
# Generic, user-facing error message (matches Module 11 in the MVP doc)
CONNECTION_ERROR_MESSAGE = "Unable to connect. Please try again later."
 
 
def _safe_get(url, params=None):
    """
    Internal helper: performs a GET request with timeout + retry logic
    and always returns the standard result dict described above.
 
    This function is "private" (leading underscore) because outside
    modules should call the higher-level functions below, not this one
    directly — keeps the public API of this module small and intentional.
    """
    last_error = None
 
    for attempt in range(1, MAX_RETRIES + 2):  # e.g. MAX_RETRIES=2 -> 3 total tries
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
 
            # Raise an exception for HTTP error codes (4xx, 5xx)
            response.raise_for_status()
 
            try:
                data = response.json()
            except ValueError:
                # Response wasn't valid JSON — treat as a failure rather
                # than letting the GUI crash trying to parse it.
                return {
                    "success": False,
                    "data": None,
                    "error": CONNECTION_ERROR_MESSAGE,
                }
 
            return {"success": True, "data": data, "error": None}
 
        except requests.exceptions.Timeout:
            last_error = "timeout"
        except requests.exceptions.ConnectionError:
            last_error = "connection_error"
        except requests.exceptions.HTTPError:
            last_error = "http_error"
        except requests.exceptions.RequestException:
            last_error = "unknown_request_error"
 
        # Small backoff before retrying (avoids hammering the API instantly)
        if attempt <= MAX_RETRIES:
            time.sleep(0.5 * attempt)
 
    # All attempts failed
    return {
        "success": False,
        "data": None,
        "error": CONNECTION_ERROR_MESSAGE,
        "_debug_reason": last_error,  # kept only for developer debugging/logs
    }
 
 
# ---------------------------------------------------------------------------
# FakeStore API wrapper functions
# ---------------------------------------------------------------------------
 
def get_fakestore_products():
    """Fetch all products from FakeStore API."""
    return _safe_get(FAKESTORE_ENDPOINTS["all_products"])
 
 
def get_fakestore_categories():
    """Fetch the list of available categories from FakeStore API."""
    return _safe_get(FAKESTORE_ENDPOINTS["categories"])
 
 
def get_fakestore_products_by_category(category):
    """Fetch products belonging to a specific category."""
    url = FAKESTORE_ENDPOINTS["products_by_category"].format(category=category)
    return _safe_get(url)
 
 
# ---------------------------------------------------------------------------
# DummyJSON API wrapper functions
# ---------------------------------------------------------------------------
 
def get_dummyjson_products(limit=100):
    """
    Fetch products from DummyJSON API.
    `limit` controls how many products come back in one call
    (DummyJSON paginates; default API limit is 30).
    """
    return _safe_get(DUMMYJSON_ENDPOINTS["all_products"], params={"limit": limit})
 
 
def search_dummyjson_products(keyword):
    """Search DummyJSON products by keyword (Module 2 — Product Search)."""
    return _safe_get(DUMMYJSON_ENDPOINTS["search"], params={"q": keyword})
 
 
def get_dummyjson_categories():
    """Fetch the list of available categories from DummyJSON API."""
    return _safe_get(DUMMYJSON_ENDPOINTS["categories"])
 
 
def get_dummyjson_products_by_category(category):
    """Fetch products belonging to a specific category from DummyJSON."""
    url = DUMMYJSON_ENDPOINTS["products_by_category"].format(category=category)
    return _safe_get(url)
 
 
# ---------------------------------------------------------------------------
# Quick manual test (only runs if this file is executed directly)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Testing FakeStore products fetch...")
    result = get_fakestore_products()
    if result["success"]:
        print(f"Success! Retrieved {len(result['data'])} products.")
    else:
        print(f"Failed: {result['error']}")
 
    print("\nTesting DummyJSON search for 'phone'...")
    result = search_dummyjson_products("phone")
    if result["success"]:
        print(f"Success! Retrieved {result['data'].get('total', 0)} matching products.")
    else:
        print(f"Failed: {result['error']}")