"""
recommendation/recommender.py
-------------------------------
Module 6 — Recommendation Engine (orchestration half)

Responsibility:
    This is the single entry point the GUI calls to get recommendations.
    It implements the exact "Recommendation Algorithm" flow from the
    MVP doc:

        Fetch Products
             |
        Filter Category
             |
        Filter Price
             |
        Filter Rating
             |
        Calculate Score
             |
        Sort
             |
        Top 5 Products

    Design decision:
        The GUI should never need to import api_client, filters, AND
        ranking separately and wire them together itself — that would
        duplicate this orchestration logic in every screen that needs
        recommendations. Instead, gui/ only ever calls ONE function
        from this file (get_recommendations). This matches the
        "Recommendation Engine" box in the Project Architecture
        diagram sitting between the GUI and the API Manager/Ranking
        Algorithm.
"""

import time
from concurrent.futures import ThreadPoolExecutor

from api.api_client import (
    get_fakestore_products,
    get_dummyjson_products,
    CONNECTION_ERROR_MESSAGE,
)
from recommendation.filters import normalize_products, apply_all_filters
from recommendation.ranking import rank_products

# ---------------------------------------------------------------------------
# Simple in-memory cache
# ---------------------------------------------------------------------------
# Design decision: without this, EVERY search (and the initial category
# load) re-fetches the entire catalog from both APIs from scratch, even
# though product data doesn't meaningfully change minute-to-minute for a
# demo/catalog API like these. That was the single biggest cause of
# "search feels slow" — most of the wait was repeated network round-trips
# for data we already had.
#
# CACHE_TTL_SECONDS controls how long a fetch is considered "fresh". A
# short TTL (rather than caching forever) still means the app picks up
# genuinely new/changed data periodically, without paying the network
# cost on every click.
_cache = {"data": None, "timestamp": 0}
CACHE_TTL_SECONDS = 120


def _fetch_and_normalize_all_products(force_refresh=False):
    """
    Fetch products from BOTH APIs and normalize them into one combined
    list. Returns a dict: {"success": bool, "data": [...], "error": str|None}

    Design decision — why combine both APIs instead of picking one:
        The MVP doc lists both FakeStore and DummyJSON as data sources,
        each contributing different strengths (FakeStore's simplicity,
        DummyJSON's brand/discount/stock fields). Combining them gives
        the recommendation engine a richer, larger pool of products to
        rank from, which produces more meaningful "Top 5" results than
        either source alone would for a small demo dataset.

    Design decision — parallel fetching:
        The two API calls don't depend on each other, so there is no
        reason to wait for FakeStore to fully finish before starting
        DummyJSON. Running both on a small thread pool means total wait
        time is roughly max(fakestore_time, dummyjson_time) instead of
        fakestore_time + dummyjson_time — close to a 2x speedup on the
        network-bound part of every search.

    Error handling:
        If ONE api fails but the other succeeds, we still return
        whatever data we DID get (partial success) rather than failing
        the whole request. We only report total failure if BOTH calls
        fail.
    """
    now = time.time()
    if not force_refresh and _cache["data"] is not None and (now - _cache["timestamp"]) < CACHE_TTL_SECONDS:
        return _cache["data"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        fakestore_future = executor.submit(get_fakestore_products)
        dummyjson_future = executor.submit(get_dummyjson_products)
        fakestore_result = fakestore_future.result()
        dummyjson_result = dummyjson_future.result()

    combined_products = []
    fakestore_ok = fakestore_result["success"]
    dummyjson_ok = dummyjson_result["success"]

    if fakestore_ok:
        combined_products += normalize_products(fakestore_result["data"], source="fakestore")

    if dummyjson_ok:
        # DummyJSON wraps its list inside {"products": [...]}
        raw_list = dummyjson_result["data"].get("products", [])
        combined_products += normalize_products(raw_list, source="dummyjson")

    if not fakestore_ok and not dummyjson_ok:
        # Module 11 — Error Handling: both sources failed.
        # Deliberately NOT cached, so the next search retries the
        # network rather than being stuck repeating a failure.
        return {"success": False, "data": [], "error": CONNECTION_ERROR_MESSAGE}

    result = {"success": True, "data": combined_products, "error": None}
    _cache["data"] = result
    _cache["timestamp"] = now
    return result


def fetch_all_products():
    """
    Public wrapper around the internal fetch+normalize step, exposed so
    the GUI can pull the full combined product list once — mainly to
    populate the category dropdown (Module 3) with categories that
    genuinely exist right now, rather than a hardcoded guess. See the
    "smartphones category" bug we hit during development for why this
    matters: assumed category names can silently not exist or not be
    in a partial page of API results.
    """
    return _fetch_and_normalize_all_products()


def get_recommendations(keyword=None, category=None, min_price=None, max_price=None, min_rating=None, top_n=5):
    """
    The main function the GUI calls.

    Parameters mirror the "Recommendation Algorithm" input in the MVP
    doc (Category, Budget, Minimum Rating), plus min_price for
    completeness since Module 4 supports a full price RANGE, not just
    a maximum budget, and `keyword` for Module 2's search bar.

    Returns:
        {
            "success": bool,
            "data": [ <scored, sorted product dicts>, ... ],  # top_n items
            "error": str or None
        }

    Example (matches the doc's worked example):
        get_recommendations(category="electronics", max_price=20000, min_rating=4)
    """
    fetch_result = _fetch_and_normalize_all_products()
    if not fetch_result["success"]:
        return fetch_result  # already in the correct {"success","data","error"} shape

    all_products = fetch_result["data"]

    # Step: Keyword -> Filter Category -> Filter Price -> Filter Rating
    filtered_products = apply_all_filters(
        all_products,
        keyword=keyword,
        category=category,
        min_price=min_price,
        max_price=max_price,
        min_rating=min_rating,
    )

    if not filtered_products:
        # Not an API failure — just no matches. The GUI should show a
        # "no products match your filters" message, NOT the connection
        # error message, so we return success=True with an empty list.
        return {"success": True, "data": [], "error": None}

    # Step: Calculate Score -> Sort -> Top N
    top_products = rank_products(filtered_products, top_n=top_n)

    return {"success": True, "data": top_products, "error": None}


# ---------------------------------------------------------------------------
# Quick manual test (requires network access to FakeStore/DummyJSON)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("Fetching recommendations: category=electronics, max_price=500, min_rating=4.0 ...\n")
    result = get_recommendations(category="electronics", max_price=500, min_rating=4.0, top_n=5)

    if not result["success"]:
        print("ERROR:", result["error"])
    elif not result["data"]:
        print("No products matched your filters.")
    else:
        for rank, product in enumerate(result["data"], start=1):
            print(f"{rank}. [{product['score']}] {product['title']} — ${product['price']} ({product['source']})")