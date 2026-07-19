"""
gui/home.py
-----------
Module 1 — Home Screen (real implementation, replaces the earlier stub)

Features (per MVP doc):
    - Application logo / title
    - Search bar (kept simple for MVP: filters by keyword in title)
    - Category dropdown (Module 3)
    - Price filter: min/max (Module 4)
    - Rating filter (Module 5)
    - "Get Recommendations" button -> Module 6 (Recommendation Engine)

Design decision — threading:
    Network calls (fetching from FakeStore/DummyJSON) can take a
    second or two, sometimes longer. Tkinter is single-threaded: any
    code running directly on a button click BLOCKS the entire window,
    including redraws, until it returns. If we called the recommender
    directly inside the button handler, the whole app would appear to
    freeze during every search. Instead, we run the network+scoring
    work on a background `threading.Thread`, and use `self.after(...)`
    to safely hand the result back to the main thread for updating
    widgets (Tkinter widgets must only be touched from the main thread).

Design decision — category dropdown populated live:
    Rather than hardcoding category names (which we learned the hard
    way can be wrong or incomplete — see the "smartphones" bug during
    development), the dropdown is populated from a real API fetch on
    startup, via recommendation.recommender.fetch_all_products().
"""

import threading
import customtkinter as ctk

from recommendation.recommender import get_recommendations, fetch_all_products
from recommendation.filters import get_available_categories
from gui.product_card import ProductCard
from gui.details import ProductDetailsWindow
from gui.compare import ProductComparisonWindow

CARDS_PER_ROW = 4


class HomeScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        # Module 8 — Product Comparison state. `_compare_selection` holds
        # up to 2 selected products; `_card_by_product_id` lets us find
        # and un-check a specific card's checkbox from outside the card
        # itself (needed when enforcing the 2-item limit).
        self._compare_selection = []
        self._card_by_product_id = {}

        self._build_header()
        self._build_filter_bar()
        self._build_results_area()
        self._build_status_label()

        # Populate the category dropdown asynchronously so the app
        # doesn't freeze on startup while fetching the product catalog.
        self._load_categories_in_background()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_header(self):
        header = ctk.CTkLabel(
            self, text="\U0001F6CD  Product Recommendation System",
            font=("Arial", 24, "bold"),
        )
        header.pack(pady=(20, 10))

    def _build_filter_bar(self):
        filter_bar = ctk.CTkFrame(self)
        filter_bar.pack(pady=10, padx=20, fill="x")

        # Search bar (Module 2 — Product Search keyword)
        self.search_entry = ctk.CTkEntry(filter_bar, placeholder_text="Search products (e.g. Laptop)", width=220)
        self.search_entry.grid(row=0, column=0, padx=8, pady=10)

        # Category dropdown (Module 3) — starts with just "All" until
        # the real category list finishes loading in the background.
        self.category_var = ctk.StringVar(value="All")
        self.category_dropdown = ctk.CTkOptionMenu(
            filter_bar, variable=self.category_var, values=["All"],
        )
        self.category_dropdown.grid(row=0, column=1, padx=8, pady=10)

        # Price filter (Module 4)
        self.min_price_entry = ctk.CTkEntry(filter_bar, placeholder_text="Min price", width=90)
        self.min_price_entry.grid(row=0, column=2, padx=8, pady=10)

        self.max_price_entry = ctk.CTkEntry(filter_bar, placeholder_text="Max price", width=90)
        self.max_price_entry.grid(row=0, column=3, padx=8, pady=10)

        # Rating filter (Module 5)
        self.rating_var = ctk.StringVar(value="Any rating")
        self.rating_dropdown = ctk.CTkOptionMenu(
            filter_bar, variable=self.rating_var,
            values=["Any rating", "2\u2605 and above", "3\u2605 and above", "4\u2605 and above", "4.5\u2605 and above"],
        )
        self.rating_dropdown.grid(row=0, column=4, padx=8, pady=10)

        # Recommend button (Module 6 trigger)
        self.recommend_button = ctk.CTkButton(
            filter_bar, text="Get Recommendations", command=self._on_recommend_clicked,
        )
        self.recommend_button.grid(row=0, column=5, padx=8, pady=10)

    def _build_results_area(self):
        # Small toolbar above results for comparison actions (Module 8).
        # Kept separate from the main filter bar since it acts on
        # SELECTED results, not on the search itself.
        compare_bar = ctk.CTkFrame(self, fg_color="transparent")
        compare_bar.pack(fill="x", padx=20)

        self.compare_button = ctk.CTkButton(
            compare_bar, text="Compare Selected (0/2)", state="disabled",
            command=self._on_compare_clicked,
        )
        self.compare_button.pack(side="left", pady=(0, 8))

        # Scrollable so any number of results can be shown without
        # resizing the window (important once real catalogs return
        # dozens of matches).
        self.results_frame = ctk.CTkScrollableFrame(self, label_text="Results")
        self.results_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))

    def _build_status_label(self):
        # Shows loading state, error messages (Module 11), or "no
        # matches" messaging — separate from the results area so it's
        # always visible regardless of how many cards are showing.
        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 12))
        self.status_label.pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Category loading (background thread)
    # ------------------------------------------------------------------

    def _load_categories_in_background(self):
        self.status_label.configure(text="Loading categories...")

        def worker():
            result = fetch_all_products()
            # Hand the result back to the MAIN thread — Tkinter widgets
            # must never be touched directly from a background thread.
            self.after(0, lambda: self._on_categories_loaded(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_categories_loaded(self, result):
        if result["success"] and result["data"]:
            categories = ["All"] + get_available_categories(result["data"])
            self.category_dropdown.configure(values=categories)
            self.status_label.configure(text="")
        else:
            # Not fatal — user can still try searching, and will get
            # the proper error message then. We just can't populate
            # the dropdown with live categories right now.
            self.status_label.configure(
                text="Could not load categories. You can still search using 'All'."
            )

    # ------------------------------------------------------------------
    # Recommend button handler (background thread)
    # ------------------------------------------------------------------

    def _on_recommend_clicked(self):
        # Parse filter inputs. Invalid numeric input (e.g. letters in
        # the price box) is handled gracefully instead of crashing —
        # we simply treat it as "no bound specified".
        keyword = self.search_entry.get()
        category = self.category_var.get()
        min_price = self._parse_float_or_none(self.min_price_entry.get())
        max_price = self._parse_float_or_none(self.max_price_entry.get())
        min_rating = self._parse_rating_selection(self.rating_var.get())

        self.recommend_button.configure(state="disabled", text="Loading...")
        self.status_label.configure(text="Fetching recommendations...")
        self._clear_results()

        def worker():
            result = get_recommendations(
                keyword=keyword, category=category, min_price=min_price, max_price=max_price,
                min_rating=min_rating, top_n=8,
            )
            self.after(0, lambda: self._on_recommendations_loaded(result))

        threading.Thread(target=worker, daemon=True).start()

    def _on_recommendations_loaded(self, result):
        self.recommend_button.configure(state="normal", text="Get Recommendations")

        if not result["success"]:
            # Module 11 — Error Handling
            self.status_label.configure(text=f"\u26A0 {result['error']}")
            return

        products = result["data"]
        if not products:
            self.status_label.configure(text="No products match your filters. Try widening them.")
            return

        self.status_label.configure(text=f"Showing {len(products)} recommendation(s)")
        self._render_product_cards(products)

    # ------------------------------------------------------------------
    # Results rendering
    # ------------------------------------------------------------------

    def _clear_results(self):
        for widget in self.results_frame.winfo_children():
            widget.destroy()
        # A fresh search invalidates any previous comparison selection —
        # the previously-selected cards no longer exist.
        self._compare_selection = []
        self._card_by_product_id = {}
        self._update_compare_button()

    def _render_product_cards(self, products):
        self._clear_results()
        for index, product in enumerate(products):
            row, col = divmod(index, CARDS_PER_ROW)
            card = ProductCard(
                self.results_frame, product,
                on_click=self._on_card_clicked,
                on_compare_toggle=self._on_compare_toggle,
            )
            card.grid(row=row, column=col, padx=10, pady=10)
            self._card_by_product_id[product["id"]] = card

    def _on_card_clicked(self, product):
        # Module 7 — Product Details. Opens as a separate popup window
        # (CTkToplevel) so the search results behind it stay untouched.
        ProductDetailsWindow(self, product)

    # ------------------------------------------------------------------
    # Module 8 — Product Comparison
    # ------------------------------------------------------------------

    def _on_compare_toggle(self, product, is_checked):
        if is_checked:
            if len(self._compare_selection) >= 2:
                # Enforce the 2-product limit: reject the 3rd selection
                # by immediately un-checking it, and tell the user why.
                card = self._card_by_product_id.get(product["id"])
                if card:
                    card.set_compare_checked(False)
                self.status_label.configure(
                    text="You can only compare 2 products at a time. Uncheck one first."
                )
                return
            self._compare_selection.append(product)
        else:
            self._compare_selection = [
                p for p in self._compare_selection if p["id"] != product["id"]
            ]

        self._update_compare_button()

    def _update_compare_button(self):
        count = len(self._compare_selection)
        self.compare_button.configure(text=f"Compare Selected ({count}/2)")
        self.compare_button.configure(state="normal" if count == 2 else "disabled")

    def _on_compare_clicked(self):
        if len(self._compare_selection) != 2:
            return  # button should be disabled in this case anyway
        product_a, product_b = self._compare_selection
        ProductComparisonWindow(self, product_a, product_b)

    # ------------------------------------------------------------------
    # Small parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_float_or_none(text):
        text = text.strip()
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None

    @staticmethod
    def _parse_rating_selection(selection):
        if selection == "Any rating":
            return None
        # e.g. "4\u2605 and above" -> 4.0
        return float(selection.split("\u2605")[0])