"""
recommendation/filters.py
-------------------------
Modules 2, 3, 4, 5 — Product Search support + Category/Price/Rating Filters

Responsibility:
    1. Normalize raw JSON from FakeStore and DummyJSON into ONE consistent
       product shape, so the rest of the app (ranking, GUI) never needs
       to know which API a product came from.
    2. Provide simple, composable filter functions for category, price,
       and rating — used both by the GUI's individual filter controls
       (Modules 3-5) and by the recommendation engine (Module 6), which
       chains all three together before scoring.

Design decision (important for report/viva):
    FakeStore and DummyJSON structure their JSON differently. For example:

        FakeStore:   {"rating": {"rate": 4.3, "count": 120}}
        DummyJSON:   {"rating": 4.3, "stock": 45}   (no "count" of reviews;
                                                       "stock" is used
                                                       instead as an
                                                       availability signal)

    Rather than writing separate filter/ranking logic for each API (which
    would duplicate code and double the bugs), we convert every product
    into ONE normalized dictionary shape the moment it arrives from the
    API client. Everything downstream — filters, ranking, GUI — only
    ever sees this normalized shape. This is the same principle as the
    "Adapter Pattern" in software engineering: isolate an external,
    inconsistent format behind a single, consistent internal interface.

Normalized product shape (used everywhere else in the project):
    {
        "id": str,                 # unique id, prefixed with source to avoid clashes
        "source": str,             # "fakestore" or "dummyjson"
        "title": str,
        "price": float,
        "category": str,
        "rating": float,           # 0.0 - 5.0
        "review_count": int,       # 0 if unknown
        "discount_percentage": float,  # 0.0 if unknown
        "stock": int,              # -1 if unknown/not provided
        "brand": str,              # "" if unknown (FakeStore has no brand field)
        "image": str,              # URL
        "description": str,
    }
"""


# ---------------------------------------------------------------------------
# Normalizers — one per source API
# ---------------------------------------------------------------------------

def normalize_fakestore_product(raw):
    """
    Convert a single raw FakeStore product dict into the normalized shape.

    FakeStore does not provide: brand, discount, stock.
    We default those to values that clearly mean "not available" (0, -1, "")
    rather than guessing, so the ranking engine (Module 6) can treat
    them fairly (e.g. discount defaults to 0%, not penalizing FakeStore
    products, but also not fabricating a discount that doesn't exist).
    """
    rating_info = raw.get("rating") or {}
    return {
        "id": f"fakestore-{raw.get('id')}",
        "source": "fakestore",
        "title": raw.get("title", "Untitled Product"),
        "price": float(raw.get("price", 0)),
        "category": raw.get("category", "uncategorized"),
        "rating": float(rating_info.get("rate", 0)),
        "review_count": int(rating_info.get("count", 0)),
        "discount_percentage": 0.0,   # FakeStore has no discount field
        "stock": -1,                  # FakeStore has no stock field
        "brand": "",                  # FakeStore has no brand field
        "image": raw.get("image", ""),
        "description": raw.get("description", ""),
    }


def normalize_dummyjson_product(raw):
    """
    Convert a single raw DummyJSON product dict into the normalized shape.

    DummyJSON does not provide a review "count" the way FakeStore does —
    it provides `stock` instead. We still map what's available so the
    ranking engine's "Popularity" factor (Module 6) can substitute
    `stock` as a rough popularity proxy when `review_count` is missing.
    """
    return {
        "id": f"dummyjson-{raw.get('id')}",
        "source": "dummyjson",
        "title": raw.get("title", "Untitled Product"),
        "price": float(raw.get("price", 0)),
        "category": raw.get("category", "uncategorized"),
        "rating": float(raw.get("rating", 0)),
        "review_count": 0,             # DummyJSON has no explicit review count
        "discount_percentage": float(raw.get("discountPercentage", 0)),
        "stock": int(raw.get("stock", -1)),
        "brand": raw.get("brand", ""),
        "image": raw.get("thumbnail", ""),
        "description": raw.get("description", ""),
    }


def normalize_products(raw_products, source):
    """
    Normalize a LIST of raw products from a given source.

    `source` must be "fakestore" or "dummyjson". Keeping this as an
    explicit parameter (instead of trying to auto-detect the shape)
    avoids fragile guessing logic — the caller (api_client.py results)
    already knows which endpoint it called, so it can just say so.
    """
    if source == "fakestore":
        return [normalize_fakestore_product(p) for p in raw_products]
    elif source == "dummyjson":
        return [normalize_dummyjson_product(p) for p in raw_products]
    else:
        raise ValueError(f"Unknown product source: {source!r}")


def get_available_categories(products):
    """
    Return a sorted list of every distinct category actually present in
    a list of normalized products.

    Design decision: the GUI's category dropdown (Module 3) should be
    populated from THIS function's output, not from a hardcoded list
    typed by hand. Live APIs can rename, add, or remove categories over
    time (we hit exactly this during development — assumed "smartphones"
    existed, but the live catalog only exposed it once we fetched the
    FULL product set). Reading categories directly from fetched data
    means the dropdown can never go stale or offer a category with zero
    matching products.
    """
    return sorted(set(p["category"] for p in products))


# ---------------------------------------------------------------------------
# Module 3 — Category Filter
# ---------------------------------------------------------------------------

def filter_by_category(products, category):
    """
    Return only products matching `category`.

    Comparison is case-insensitive and trims whitespace, since category
    strings come from two different APIs with slightly different casing
    conventions (e.g. "Men's Clothing" vs "mens-shirts").

    `category=None` or `category="All"` returns the full list unfiltered —
    this matches the GUI's category dropdown having an "All Categories"
    option by default.
    """
    if not category or category.strip().lower() == "all":
        return products

    target = category.strip().lower()
    return [p for p in products if p["category"].strip().lower() == target]


# ---------------------------------------------------------------------------
# Module 4 — Price Filter
# ---------------------------------------------------------------------------

def filter_by_price(products, min_price=None, max_price=None):
    """
    Return only products whose price falls within [min_price, max_price].

    Both bounds are optional and inclusive:
      - min_price=None means "no lower bound"
      - max_price=None means "no upper bound"
    This lets the GUI call this function even if the user only fills in
    one of the two price fields, without needing special-case code.
    """
    result = products

    if min_price is not None:
        result = [p for p in result if p["price"] >= min_price]

    if max_price is not None:
        result = [p for p in result if p["price"] <= max_price]

    return result


# ---------------------------------------------------------------------------
# Module 5 — Rating Filter
# ---------------------------------------------------------------------------

def filter_by_rating(products, min_rating=None):
    """
    Return only products with rating >= min_rating.

    Example from the MVP doc: user picks "4★ and above" -> min_rating=4.0
    """
    if min_rating is None:
        return products

    return [p for p in products if p["rating"] >= min_rating]


# ---------------------------------------------------------------------------
# Convenience: apply all filters in one call
# (used by recommendation/recommender.py per the Algorithm Flow in the doc:
#  Fetch -> Filter Category -> Filter Price -> Filter Rating -> Score -> Sort)
# ---------------------------------------------------------------------------

def apply_all_filters(products, category=None, min_price=None, max_price=None, min_rating=None):
    """
    Chain category -> price -> rating filters in the exact order shown
    in the MVP doc's "Recommendation Algorithm" flow diagram.

    Order matters slightly for performance (cheapest/most-likely-to-
    eliminate filters first is generally better), but for this dataset
    size (dozens-hundreds of products) it makes no noticeable difference —
    we follow the doc's documented order for consistency and clarity.
    """
    filtered = filter_by_category(products, category)
    filtered = filter_by_price(filtered, min_price, max_price)
    filtered = filter_by_rating(filtered, min_rating)
    return filtered


# ---------------------------------------------------------------------------
# Quick manual test with sample data (no network needed)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_fakestore_raw = [
        {
            "id": 1, "title": "Fjallraven Backpack", "price": 109.95,
            "category": "men's clothing",
            "description": "A durable backpack.",
            "image": "https://example.com/backpack.jpg",
            "rating": {"rate": 3.9, "count": 120},
        },
        {
            "id": 2, "title": "Slim Fit T-Shirt", "price": 22.3,
            "category": "men's clothing",
            "description": "A comfortable t-shirt.",
            "image": "https://example.com/tshirt.jpg",
            "rating": {"rate": 4.6, "count": 259},
        },
    ]

    sample_dummyjson_raw = [
        {
            "id": 101, "title": "iPhone 9", "price": 549,
            "category": "smartphones", "brand": "Apple",
            "description": "An older iPhone model.",
            "thumbnail": "https://example.com/iphone9.jpg",
            "rating": 4.69, "discountPercentage": 12.96, "stock": 94,
        },
        {
            "id": 102, "title": "Samsung Universe 9", "price": 1249,
            "category": "smartphones", "brand": "Samsung",
            "description": "Samsung flagship phone.",
            "thumbnail": "https://example.com/samsung9.jpg",
            "rating": 2.25, "discountPercentage": 15.46, "stock": 36,
        },
    ]

    normalized = (
        normalize_products(sample_fakestore_raw, source="fakestore")
        + normalize_products(sample_dummyjson_raw, source="dummyjson")
    )

    print(f"Total normalized products: {len(normalized)}")

    high_rated = filter_by_rating(normalized, min_rating=4.0)
    print(f"\nProducts rated 4.0+: {[p['title'] for p in high_rated]}")

    under_100 = filter_by_price(normalized, max_price=100)
    print(f"Products under $100: {[p['title'] for p in under_100]}")

    smartphones = filter_by_category(normalized, "smartphones")
    print(f"Smartphones: {[p['title'] for p in smartphones]}")

    combo = apply_all_filters(normalized, category="smartphones", min_rating=4.0)
    print(f"\nSmartphones rated 4.0+: {[p['title'] for p in combo]}")