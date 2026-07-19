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

    Images are downloaded ASYNCHRONOUSLY on a background thread per
    card, not while the card is being built. Originally, image
    downloads happened synchronously during widget construction — with
    8 results, that meant waiting for 8 sequential image downloads,
    one after another, before the results screen felt "done" loading,
    even though the actual product DATA had already arrived instantly.
    Now every card appears immediately with a placeholder, and each
    image quietly pops in as its own download finishes — a much better
    perceived-performance experience, and it matches how virtually
    every real shopping app/website behaves.

    A small in-memory cache (keyed by URL) also avoids re-downloading
    the same image twice if the same product appears in a later search.
"""

import io
import threading
import requests
import customtkinter as ctk
from PIL import Image

from utils.helpers import truncate_text

CARD_WIDTH = 220
CARD_HEIGHT = 320
IMAGE_SIZE = (160, 160)

# Shared across all cards: once an image URL has been downloaded once,
# every future card for that same product reuses it instantly instead
# of hitting the network again.
_image_cache = {}


def _download_and_decode_image(url):
    """
    Download and decode a product image from `url`.
    Returns a CTkImage, or None if it couldn't be loaded (caller should
    show a placeholder in that case). This function does real network
    I/O and should only ever be called from a background thread.
    """
    if not url:
        return None
    if url in _image_cache:
        return _image_cache[url]
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        pil_image = Image.open(io.BytesIO(response.content)).convert("RGB")
        pil_image = pil_image.resize(IMAGE_SIZE)
        ctk_image = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=IMAGE_SIZE)
        _image_cache[url] = ctk_image
        return ctk_image
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

    `on_compare_toggle`: optional callback, called with (product, is_checked)
    when the compare checkbox is toggled — used by Module 8 (Comparison)
    to track which products are currently selected for a side-by-side
    comparison. Checkbox clicks intentionally do NOT trigger `on_click`
    (opening details) — the two actions target different intents and
    shouldn't fire together.
    """

    def __init__(self, master, product, on_click=None, on_compare_toggle=None):
        super().__init__(master, width=CARD_WIDTH, height=CARD_HEIGHT, corner_radius=10)
        self.grid_propagate(False)  # keep every card the same size regardless of content
        self.product = product
        self.on_click = on_click
        self.on_compare_toggle = on_compare_toggle

        # Show a placeholder immediately — the card should never make
        # the user wait on a network call just to appear on screen.
        self.image_label = ctk.CTkLabel(
            self, text="Loading...", width=IMAGE_SIZE[0], height=IMAGE_SIZE[1],
            fg_color="gray85", corner_radius=8,
        )
        self.image_label.pack(pady=(12, 8))
        self._load_image_in_background(product.get("image"))

        title_label = ctk.CTkLabel(
            self,
            text=truncate_text(product.get("title", "Untitled"), 40),
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

        # Compare checkbox (Module 8) — deliberately placed BEFORE the
        # click-binding loop below, so clicking it toggles comparison
        # selection only, without also opening the details popup.
        if self.on_compare_toggle:
            self.compare_var = ctk.BooleanVar(value=False)
            self.compare_checkbox = ctk.CTkCheckBox(
                self, text="Compare", variable=self.compare_var,
                command=self._handle_compare_toggle, font=("Arial", 11),
            )
            self.compare_checkbox.pack(pady=(0, 6))

        # Make the whole card clickable, not just one label inside it
        if self.on_click:
            self.bind("<Button-1>", self._handle_click)
            for child in self.winfo_children():
                # Skip the checkbox itself — it has its own click handling
                # and shouldn't ALSO open the details popup when toggled.
                if self.on_compare_toggle and child is self.compare_checkbox:
                    continue
                child.bind("<Button-1>", self._handle_click)

    def _handle_click(self, event):
        if self.on_click:
            self.on_click(self.product)

    def _handle_compare_toggle(self):
        if self.on_compare_toggle:
            self.on_compare_toggle(self.product, self.compare_var.get())

    def set_compare_checked(self, checked):
        """
        Externally force this card's checkbox state — used by HomeScreen
        to un-check a card when the 2-selection limit is enforced from
        outside this widget (e.g. the user tries to select a 3rd product).
        """
        if self.on_compare_toggle:
            self.compare_var.set(checked)

    def _load_image_in_background(self, url):
        def worker():
            image = _download_and_decode_image(url)
            # Hand the result back to the main thread. We guard with
            # winfo_exists() because the user may have run a NEW search
            # (which clears and rebuilds all cards) before this
            # download finishes — trying to update a destroyed widget
            # would raise a TclError.
            self.after(0, lambda: self._on_image_loaded(image))

        threading.Thread(target=worker, daemon=True).start()

    def _on_image_loaded(self, image):
        if not self.winfo_exists():
            return
        if image:
            self.image_label.configure(image=image, text="")
        else:
            self.image_label.configure(text="No Image", fg_color="gray75")