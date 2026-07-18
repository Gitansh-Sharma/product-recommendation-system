"""
gui/product_card.py
--------------------
Module 2 support — Product display widget.

Responsibility:
    A single reusable "card" widget showing one product's image, name,
    price, rating, and category — exactly the fields Module 2 (Product
    Search) says should be displayed per result.

Design decision:
    This is its OWN small class (not inline code inside home.py)
    because it will be reused in at least two places: the main results
    list (Module 2) and, later, the comparison screen (Module 8). Any
    change to how a product looks (e.g. adding a "brand" line) only
    needs to happen here, once.

Design decision — image loading:
    Product images come from a URL, not a local file, so we download
    the bytes with `requests` and decode them with Pillow. If the
    image fails to load (bad URL, network hiccup, unsupported format),
    we fall back to a plain gray placeholder rather than crashing the
    whole card — a smaller-scale version of the same "graceful failure"
    principle as Module 11's API error handling.
"""

import io
import requests
import customtkinter as ctk
from PIL import Image

CARD_WIDTH = 220
CARD_HEIGHT = 320
IMAGE_SIZE = (160, 160)


def _load_product_image(url):
    """
    Download and decode a product image from `url`.
    Returns a CTkImage, or None if it couldn't be loaded (caller should
    show a placeholder in that case).
    """
    if not url:
        return None
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        pil_image = Image.open(io.BytesIO(response.content)).convert("RGB")
        pil_image = pil_image.resize(IMAGE_SIZE)
        return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=IMAGE_SIZE)
    except Exception:
        # Broad except is intentional here: ANY image problem (timeout,
        # bad URL, corrupt file, unsupported format) should degrade to
        # "no image" rather than propagate and break the whole product
        # list from rendering.
        return None


class ProductCard(ctk.CTkFrame):
    """
    A single product tile.

    `product` is a normalized+scored product dict (see
    recommendation/filters.py and ranking.py for the shape).

    `on_click`: optional callback, called with `product` when the card
    is clicked — wired up later to open Module 7 (Product Details).
    """

    def __init__(self, master, product, on_click=None):
        super().__init__(master, width=CARD_WIDTH, height=CARD_HEIGHT, corner_radius=10)
        self.grid_propagate(False)  # keep every card the same size regardless of content
        self.product = product
        self.on_click = on_click

        image = _load_product_image(product.get("image"))
        if image:
            image_label = ctk.CTkLabel(self, image=image, text="")
        else:
            # Placeholder when image couldn't load
            image_label = ctk.CTkLabel(
                self, text="No Image", width=IMAGE_SIZE[0], height=IMAGE_SIZE[1],
                fg_color="gray75", corner_radius=8,
            )
        image_label.pack(pady=(12, 8))

        title_label = ctk.CTkLabel(
            self,
            text=self._truncate(product.get("title", "Untitled"), 40),
            font=("Arial", 13, "bold"),
            wraplength=CARD_WIDTH - 20,
            justify="center",
        )
        title_label.pack(pady=(0, 4), padx=10)

        price_label = ctk.CTkLabel(
            self, text=f"${product.get('price', 0):.2f}", font=("Arial", 14, "bold"),
            text_color="#2fa572",
        )
        price_label.pack()

        rating = product.get("rating", 0)
        rating_label = ctk.CTkLabel(self, text=f"\u2605 {rating:.1f}", font=("Arial", 12))
        rating_label.pack()

        category_label = ctk.CTkLabel(
            self, text=product.get("category", ""), font=("Arial", 11), text_color="gray60",
        )
        category_label.pack(pady=(2, 8))

        # Score badge — only shown for ranked/recommended results, since
        # a raw product listing (Module 2) has no score, only filtered
        # recommendation results (Module 6) do.
        if "score" in product:
            score_label = ctk.CTkLabel(
                self, text=f"Match score: {product['score']}", font=("Arial", 10, "italic"),
                text_color="#3b82f6",
            )
            score_label.pack(pady=(0, 8))

        # Make the whole card clickable, not just one label inside it
        if self.on_click:
            self.bind("<Button-1>", self._handle_click)
            for child in self.winfo_children():
                child.bind("<Button-1>", self._handle_click)

    def _handle_click(self, event):
        if self.on_click:
            self.on_click(self.product)

    @staticmethod
    def _truncate(text, max_len):
        return text if len(text) <= max_len else text[: max_len - 1] + "\u2026"