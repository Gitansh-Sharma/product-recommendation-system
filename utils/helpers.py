"""
utils/helpers.py
-----------------
Small, shared, dependency-free helper functions used across multiple
GUI modules.

Design decision — why extract these instead of leaving them duplicated:
    truncate_text() originally existed as a near-identical private
    method copy-pasted into product_card.py, details.py, AND compare.py.
    That's a classic code smell: if we ever wanted to change the
    truncation behavior (e.g. different ellipsis character, different
    edge-case handling), we'd have had to remember to update it in
    three separate places. Centralizing it here means one change
    propagates everywhere it's used automatically.
"""


def truncate_text(text, max_length):
    """
    Shorten `text` to at most `max_length` characters, appending an
    ellipsis if it was cut short. Used anywhere a product title or
    description needs to fit in a fixed-width UI element (cards,
    details view, comparison table).
    """
    if text is None:
        return ""
    return text if len(text) <= max_length else text[: max_length - 1] + "\u2026"


def format_price(value):
    """Format a numeric price consistently as e.g. '$19.99'."""
    try:
        return f"${float(value):.2f}"
    except (TypeError, ValueError):
        return "$0.00"


def format_rating(value):
    """Format a numeric rating consistently as e.g. '★ 4.5'."""
    try:
        return f"\u2605 {float(value):.1f}"
    except (TypeError, ValueError):
        return "\u2605 0.0"


def describe_availability(product):
    """
    Turn a normalized product's `stock` field into a human-readable
    availability string, honest about missing data rather than
    fabricating a number.

    stock == -1 means the source API doesn't provide stock data at all
    (this is true for every FakeStore product — see
    recommendation/filters.py's normalizer notes).
    """
    stock = product.get("stock", -1)
    if stock == -1:
        return "Not provided by this source"
    if stock > 0:
        return f"In stock ({stock} available)"
    return "Out of stock"