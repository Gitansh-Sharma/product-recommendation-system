"""
gui/details.py
---------------
Module 7 — Product Details

Responsibility:
    Shows the full detail view for a single product: large image,
    description, rating, price, category, brand, discount, and
    availability — exactly the field list the MVP doc specifies for
    this module.

Design decision — CTkToplevel (separate window) vs. swapping the main
frame's content:
    We use a CTkToplevel (a secondary popup window) rather than
    replacing HomeScreen's content in-place. This keeps the user's
    search results, filters, and scroll position completely intact
    behind the details window — closing it returns them to exactly
    where they were, with no need to re-run a search. It also keeps
    this module fully self-contained: HomeScreen doesn't need any
    "go back" state management, it just opens/closes a window.

Design decision — availability field:
    FakeStore products have no stock data (normalized to -1, meaning
    "unknown" — see recommendation/filters.py). DummyJSON products DO
    have real stock counts. Rather than showing a misleading "0 in
    stock" for FakeStore products, we explicitly show "Availability
    info not provided by this source" — honest about what the data
    actually contains, rather than fabricating a number.
Design decision — wishlist and recently-viewed live here, not in HomeScreen:
    Module 9 (Wishlist) and Module 10 (Recently Viewed) both hook into
    THIS window rather than the card grid, because "viewing details"
    is the natural, literal meaning of "recently viewed" — browsing a
    grid of search result cards isn't the same as actually looking at
    a product. Every time this window opens, the product is recorded
    as viewed automatically. The wishlist button reads/writes directly
    through database/database.py, the same way HomeScreen calls
    recommendation/recommender.py directly — gui/ is allowed to call
    either logic layer directly; it just never touches the network or
    SQLite itself.
"""

import io
import requests
import customtkinter as ctk
from PIL import Image

from utils.helpers import describe_availability
from database.database import add_to_wishlist, remove_from_wishlist, is_in_wishlist, add_recently_viewed

LARGE_IMAGE_SIZE = (280, 280)


def _load_large_image(url):
    """Same pattern as product_card.py's image loader, just larger."""
    if not url:
        return None
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        pil_image = Image.open(io.BytesIO(response.content)).convert("RGB")
        pil_image = pil_image.resize(LARGE_IMAGE_SIZE)
        return ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=LARGE_IMAGE_SIZE)
    except Exception:
        return None


class ProductDetailsWindow(ctk.CTkToplevel):
    """
    A popup window showing full details for one product.

    `product` is a normalized product dict (see recommendation/filters.py).
    """

    def __init__(self, master, product):
        super().__init__(master)
        self.product = product

        self.title(product.get("title", "Product Details")[:50])
        self.geometry("500x650")
        self.minsize(420, 550)

        # Keep this window on top of the main app and grab focus, so
        # it behaves like a proper modal detail view rather than
        # getting lost behind the main window.
        self.transient(master)
        self.grab_set()

        # Module 10 — Recently Viewed. Recorded the moment details are
        # opened, since that's the clearest real signal of genuine
        # interest in a product (as opposed to it merely appearing in
        # a results grid). Failure here (e.g. SQLite issue) is silently
        # non-fatal — recently-viewed is a nice-to-have, not core to
        # the app functioning.
        add_recently_viewed(product)

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # --- Large image ---
        image = _load_large_image(self.product.get("image"))
        if image:
            image_label = ctk.CTkLabel(container, image=image, text="")
        else:
            image_label = ctk.CTkLabel(
                container, text="No Image Available",
                width=LARGE_IMAGE_SIZE[0], height=LARGE_IMAGE_SIZE[1],
                fg_color="gray75", corner_radius=10,
            )
        image_label.pack(pady=(5, 15))

        # --- Title ---
        ctk.CTkLabel(
            container, text=self.product.get("title", "Untitled Product"),
            font=("Arial", 18, "bold"), wraplength=440, justify="left",
        ).pack(anchor="w", pady=(0, 10))

        # --- Price + discount ---
        price = self.product.get("price", 0)
        discount = self.product.get("discount_percentage", 0)
        if discount > 0:
            original_price = price / (1 - discount / 100) if discount < 100 else price
            price_text = f"${price:.2f}   (was ${original_price:.2f}, {discount:.0f}% off)"
        else:
            price_text = f"${price:.2f}"
        ctk.CTkLabel(
            container, text=price_text, font=("Arial", 16, "bold"), text_color="#2fa572",
        ).pack(anchor="w", pady=(0, 8))

        # --- Rating ---
        rating = self.product.get("rating", 0)
        review_count = self.product.get("review_count", 0)
        rating_text = f"\u2605 {rating:.1f} / 5.0"
        if review_count > 0:
            rating_text += f"  ({review_count} reviews)"
        ctk.CTkLabel(container, text=rating_text, font=("Arial", 13)).pack(anchor="w", pady=(0, 8))

        # --- Category / Brand ---
        self._add_field_row(container, "Category", self.product.get("category", "N/A"))
        brand = self.product.get("brand", "")
        self._add_field_row(container, "Brand", brand if brand else "Not specified by this source")

        # --- Availability (honest about missing data) ---
        self._add_field_row(container, "Availability", describe_availability(self.product))

        # --- Data source (transparency — worth mentioning in report) ---
        self._add_field_row(container, "Data source", self.product.get("source", "unknown").title())

        # --- Description ---
        ctk.CTkLabel(
            container, text="Description", font=("Arial", 13, "bold"),
        ).pack(anchor="w", pady=(15, 4))
        description = self.product.get("description", "") or "No description available."
        ctk.CTkLabel(
            container, text=description, font=("Arial", 12), wraplength=440,
            justify="left", text_color="gray70",
        ).pack(anchor="w", pady=(0, 15))

        # --- Action buttons ---
        button_row = ctk.CTkFrame(container, fg_color="transparent")
        button_row.pack(fill="x", pady=(5, 10))

        # Button label reflects current wishlist state, checked fresh
        # every time the window opens (not cached), so it's always
        # accurate even if the product was wishlisted in a previous
        # session.
        self._in_wishlist = is_in_wishlist(self.product["id"])
        self.wishlist_button = ctk.CTkButton(
            button_row, text=self._wishlist_button_text(), command=self._handle_wishlist_click,
        )
        self.wishlist_button.pack(side="left", padx=(0, 10))

        close_button = ctk.CTkButton(
            button_row, text="Close", fg_color="gray40", hover_color="gray30",
            command=self.destroy,
        )
        close_button.pack(side="left")

    def _wishlist_button_text(self):
        return "\u2764 Remove from Wishlist" if self._in_wishlist else "\u2764 Add to Wishlist"

    def _add_field_row(self, parent, label, value):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=2)
        ctk.CTkLabel(row, text=f"{label}:", font=("Arial", 12, "bold"), width=90, anchor="w").pack(side="left")
        ctk.CTkLabel(row, text=str(value), font=("Arial", 12), anchor="w").pack(side="left")

    def _handle_wishlist_click(self):
        if self._in_wishlist:
            remove_from_wishlist(self.product["id"])
            self._in_wishlist = False
        else:
            add_to_wishlist(self.product)
            self._in_wishlist = True
        self.wishlist_button.configure(text=self._wishlist_button_text())