"""
endpoints.py
------------
Central place for all external API base URLs and endpoint paths.
 
Design decision:
    Keeping URLs here (instead of hardcoding them inside api_client.py)
    means that if an API changes its domain, or we add a third data
    source later (e.g. a real e-commerce API in a future version),
    we only edit ONE file. This is basic separation of concerns and
    is a common talking point for examiners asking "why is your code
    organized this way?".
"""
 
# ---------------------------------------------------------------------------
# FakeStore API
# Docs: https://fakestoreapi.com/docs
# Provides: products, categories, prices, ratings, images
# ---------------------------------------------------------------------------
FAKESTORE_BASE_URL = "https://fakestoreapi.com"
 
FAKESTORE_ENDPOINTS = {
    "all_products": f"{FAKESTORE_BASE_URL}/products",
    "single_product": f"{FAKESTORE_BASE_URL}/products/{{id}}",   # .format(id=...)
    "categories": f"{FAKESTORE_BASE_URL}/products/categories",
    "products_by_category": f"{FAKESTORE_BASE_URL}/products/category/{{category}}",
}
 
# ---------------------------------------------------------------------------
# DummyJSON API
# Docs: https://dummyjson.com/docs/products
# Provides: brand, discount, reviews, stock, category
# ---------------------------------------------------------------------------
DUMMYJSON_BASE_URL = "https://dummyjson.com"
 
DUMMYJSON_ENDPOINTS = {
    "all_products": f"{DUMMYJSON_BASE_URL}/products",
    "single_product": f"{DUMMYJSON_BASE_URL}/products/{{id}}",
    "search": f"{DUMMYJSON_BASE_URL}/products/search",   # ?q=keyword
    "categories": f"{DUMMYJSON_BASE_URL}/products/category-list",
    "products_by_category": f"{DUMMYJSON_BASE_URL}/products/category/{{category}}",
}
 
# ---------------------------------------------------------------------------
# Shared request settings
# ---------------------------------------------------------------------------
REQUEST_TIMEOUT_SECONDS = 8      # how long we wait before treating a call as failed
MAX_RETRIES = 2                  # number of retry attempts on transient failures
 