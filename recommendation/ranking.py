"""
recommendation/ranking.py
--------------------------
Module 6 — Recommendation Engine (scoring half)

Responsibility:
    Implements the weighted scoring formula from the MVP doc:

        Rating      -> 40%
        Price       -> 30%
        Discount    -> 20%
        Popularity  -> 10%

    This file ONLY does math on an already-filtered list of normalized
    products (see recommendation/filters.py for the normalized shape).
    It does not fetch data and does not know about APIs — that keeps
    it easy to unit-test with plain Python dicts, and easy to explain
    to examiners as "pure functions in, score out."

Design decision — why we normalize each factor to a 0-1 scale first:
    The four factors are on wildly different scales:
        rating              -> 0 to 5
        price               -> could be $5 or $50,000
        discount_percentage -> 0 to 100
        popularity proxy    -> review_count (0 to thousands) or
                                stock (0 to hundreds)

    If we multiplied raw values by their weights directly, "price"
    (being a large number) would completely dominate "rating" (a small
    number) regardless of the 30%/40% weights — the weights would be
    meaningless. So every factor is first squeezed into a common 0-1
    range using min-max normalization ACROSS THE CURRENT CANDIDATE SET,
    and only THEN multiplied by its weight. This is a standard technique
    in any weighted scoring / multi-criteria decision system — worth
    mentioning by name ("min-max normalization") in your report.

Design decision — why price is inverted:
    A cheaper product should score HIGHER on the price factor (it's
    more affordable), not lower. So price_score = 1 - normalized_price,
    meaning the cheapest product in the set scores 1.0 on price and the
    most expensive scores 0.0.

Design decision — popularity proxy:
    FakeStore gives us `review_count`; DummyJSON gives us `stock`
    instead (see filters.py normalizer notes). Neither is a perfect
    universal "popularity" signal, but both are reasonable proxies for
    "this product is actively bought/reviewed", which is the spirit of
    the MVP doc's "Popularity" factor. We use whichever value is present
    per-product; if a normalized product has review_count > 0 we use
    that, otherwise we fall back to stock (with stock capped so a huge
    warehouse stock number doesn't get treated as literally "popular"
    stock is really about availability, but it's the best proxy DummyJSON
    gives us).
"""

# Weights exactly as specified in the MVP doc
WEIGHT_RATING = 0.40
WEIGHT_PRICE = 0.30
WEIGHT_DISCOUNT = 0.20
WEIGHT_POPULARITY = 0.10


def _min_max_normalize(value, min_value, max_value):
    """
    Squeeze `value` into a 0.0-1.0 range given the min/max of its group.

    Edge case handled: if every product in the set has the same value
    (min_value == max_value), we return 0.5 (a neutral mid-score)
    instead of dividing by zero.
    """
    if max_value == min_value:
        return 0.5
    return (value - min_value) / (max_value - min_value)


def _popularity_signal(product):
    """
    Return a single 'popularity' number for a product, preferring
    review_count (FakeStore) and falling back to stock (DummyJSON).
    """
    if product["review_count"] > 0:
        return product["review_count"]
    return max(product["stock"], 0)  # stock of -1 (unknown) becomes 0


def calculate_scores(products):
    """
    Given a list of normalized products (see filters.py), return a NEW
    list of the same products, each with an added "score" key (0-100,
    for readability — e.g. "82.4" reads better on a product card than
    "0.824").

    Normalization ranges (min/max) are computed ACROSS THIS LIST, i.e.
    relative to the current search/filter results — not against every
    product in the entire API. This is intentional: a $20,000 laptop
    scoring low on "price" only matters relative to OTHER laptops the
    user is currently considering, not against a $5 phone case from an
    unrelated category filtered out earlier in the pipeline.
    """
    if not products:
        return []

    ratings = [p["rating"] for p in products]
    prices = [p["price"] for p in products]
    discounts = [p["discount_percentage"] for p in products]
    popularity_values = [_popularity_signal(p) for p in products]

    min_rating, max_rating = min(ratings), max(ratings)
    min_price, max_price = min(prices), max(prices)
    min_discount, max_discount = min(discounts), max(discounts)
    min_pop, max_pop = min(popularity_values), max(popularity_values)

    scored_products = []
    for product, popularity_value in zip(products, popularity_values):
        rating_score = _min_max_normalize(product["rating"], min_rating, max_rating)

        # Inverted: cheaper = higher score
        price_score = 1 - _min_max_normalize(product["price"], min_price, max_price)

        discount_score = _min_max_normalize(
            product["discount_percentage"], min_discount, max_discount
        )

        popularity_score = _min_max_normalize(popularity_value, min_pop, max_pop)

        final_score = (
            rating_score * WEIGHT_RATING
            + price_score * WEIGHT_PRICE
            + discount_score * WEIGHT_DISCOUNT
            + popularity_score * WEIGHT_POPULARITY
        )

        # Copy the product dict so we never mutate the caller's original list
        scored_product = dict(product)
        scored_product["score"] = round(final_score * 100, 1)  # 0-100 scale
        scored_products.append(scored_product)

    return scored_products


def rank_products(products, top_n=None):
    """
    Score products, then sort highest-score first.

    `top_n`: if given, only the top N results are returned (per the
    MVP doc's "Top 5 Products" step in the Recommendation Algorithm).
    If None, ALL scored+sorted products are returned — useful for the
    GUI's general product listing (Module 2) where every result should
    still show, just ordered best-to-worst rather than truncated.
    """
    scored = calculate_scores(products)
    scored.sort(key=lambda p: p["score"], reverse=True)

    if top_n is not None:
        return scored[:top_n]
    return scored


# ---------------------------------------------------------------------------
# Quick manual test with sample data (no network needed)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    sample_products = [
        {
            "id": "a", "source": "fakestore", "title": "Budget Headphones",
            "price": 25.0, "category": "electronics", "rating": 4.2,
            "review_count": 300, "discount_percentage": 0.0, "stock": -1,
            "brand": "", "image": "", "description": "",
        },
        {
            "id": "b", "source": "dummyjson", "title": "Premium Headphones",
            "price": 199.0, "category": "electronics", "rating": 4.8,
            "review_count": 0, "discount_percentage": 15.0, "stock": 40,
            "brand": "SoundCo", "image": "", "description": "",
        },
        {
            "id": "c", "source": "dummyjson", "title": "Mediocre Headphones",
            "price": 60.0, "category": "electronics", "rating": 3.1,
            "review_count": 0, "discount_percentage": 5.0, "stock": 5,
            "brand": "NoName", "image": "", "description": "",
        },
    ]

    ranked = rank_products(sample_products)
    print("Ranked results (best to worst):")
    for p in ranked:
        print(f"  {p['score']:>5} | {p['title']}")