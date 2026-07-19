"""
gui/compare.py
---------------
Module 8 — Product Comparison

Responsibility:
    Shows two selected products side by side with the fields the MVP
    doc specifies: Price, Rating, Category, Brand, Discount — plus
    Availability, since it's already part of our normalized product
    shape and is useful comparison information.

Design decision — highlighting the better value, not just showing a checkmark:
    The MVP doc's table sketch just shows a checkmark (✔) in every cell
    for both products, meaning "this feature exists for both" — which,
    for an actual side-by-side comparison, isn't very useful; the user
    already knows both products have a price and a rating. Instead, we
    highlight WHICH of the two products wins each numeric row (cheaper
    price, higher rating, bigger discount) in green. This is a small
    but meaningful upgrade from the doc's original sketch, and directly
    demonstrates the comparison actually helping someone decide, not
    just displaying data.

Design decision — CTkToplevel, same as details.py:
    Consistent with Module 7, comparison opens as its own popup window
    rather than replacing HomeScreen's content, so search results and
    filters stay untouched underneath it.
"""

import customtkinter as ctk

from utils.helpers import truncate_text, describe_availability

WINNER_COLOR = "#2fa572"
NEUTRAL_COLOR_LIGHT = ("gray90", "gray20")


class ProductComparisonWindow(ctk.CTkToplevel):
    """
    Side-by-side comparison of exactly two products.

    `product_a`, `product_b`: normalized product dicts (see
    recommendation/filters.py for the shape).
    """

    def __init__(self, master, product_a, product_b):
        super().__init__(master)
        self.product_a = product_a
        self.product_b = product_b

        self.title("Compare Products")
        self.geometry("650x550")
        self.minsize(550, 480)
        self.transient(master)
        self.grab_set()

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self)
        container.pack(fill="both", expand=True, padx=15, pady=15)

        # --- Header row: product titles ---
        container.grid_columnconfigure(0, weight=0, minsize=110)
        container.grid_columnconfigure(1, weight=1)
        container.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(container, text="").grid(row=0, column=0)
        ctk.CTkLabel(
            container, text=truncate_text(self.product_a.get("title", "Product A"), 30),
            font=("Arial", 14, "bold"), wraplength=200, justify="center",
        ).grid(row=0, column=1, padx=8, pady=(0, 10), sticky="ew")
        ctk.CTkLabel(
            container, text=truncate_text(self.product_b.get("title", "Product B"), 30),
            font=("Arial", 14, "bold"), wraplength=200, justify="center",
        ).grid(row=0, column=2, padx=8, pady=(0, 10), sticky="ew")

        row_index = 1
        row_index = self._add_price_row(container, row_index)
        row_index = self._add_rating_row(container, row_index)
        row_index = self._add_text_row(container, row_index, "Category", "category")
        row_index = self._add_text_row(container, row_index, "Brand", "brand", default="Not specified")
        row_index = self._add_discount_row(container, row_index)
        row_index = self._add_availability_row(container, row_index)
        row_index = self._add_text_row(container, row_index, "Source", "source", transform=str.title)

        # --- Verdict line ---
        verdict = self._build_verdict()
        ctk.CTkLabel(
            container, text=verdict, font=("Arial", 12, "italic"), text_color="gray60",
            wraplength=560, justify="left",
        ).grid(row=row_index, column=0, columnspan=3, pady=(15, 5), sticky="w")
        row_index += 1

        close_button = ctk.CTkButton(container, text="Close", command=self.destroy, fg_color="gray40", hover_color="gray30")
        close_button.grid(row=row_index, column=0, columnspan=3, pady=(10, 5))

    # ------------------------------------------------------------------
    # Row builders
    # ------------------------------------------------------------------

    def _add_row(self, parent, row_index, label, value_a, value_b, winner=None):
        """
        winner: "a", "b", or None (tie / not applicable). The winning
        cell gets a green highlight so the comparison visually points
        at the better option, not just displaying two flat numbers.
        """
        ctk.CTkLabel(parent, text=label, font=("Arial", 12, "bold"), anchor="w").grid(
            row=row_index, column=0, padx=(0, 8), pady=6, sticky="w"
        )
        ctk.CTkLabel(
            parent, text=str(value_a), font=("Arial", 12),
            text_color=WINNER_COLOR if winner == "a" else None,
            fg_color=("gray85", "gray17") if winner == "a" else "transparent",
            corner_radius=6,
        ).grid(row=row_index, column=1, padx=8, pady=4, sticky="ew")
        ctk.CTkLabel(
            parent, text=str(value_b), font=("Arial", 12),
            text_color=WINNER_COLOR if winner == "b" else None,
            fg_color=("gray85", "gray17") if winner == "b" else "transparent",
            corner_radius=6,
        ).grid(row=row_index, column=2, padx=8, pady=4, sticky="ew")
        return row_index + 1

    def _add_price_row(self, parent, row_index):
        price_a = self.product_a.get("price", 0)
        price_b = self.product_b.get("price", 0)
        winner = "a" if price_a < price_b else ("b" if price_b < price_a else None)
        return self._add_row(parent, row_index, "Price", f"${price_a:.2f}", f"${price_b:.2f}", winner)

    def _add_rating_row(self, parent, row_index):
        rating_a = self.product_a.get("rating", 0)
        rating_b = self.product_b.get("rating", 0)
        winner = "a" if rating_a > rating_b else ("b" if rating_b > rating_a else None)
        return self._add_row(
            parent, row_index, "Rating",
            f"\u2605 {rating_a:.1f}", f"\u2605 {rating_b:.1f}", winner,
        )

    def _add_discount_row(self, parent, row_index):
        disc_a = self.product_a.get("discount_percentage", 0)
        disc_b = self.product_b.get("discount_percentage", 0)
        winner = "a" if disc_a > disc_b else ("b" if disc_b > disc_a else None)
        return self._add_row(parent, row_index, "Discount", f"{disc_a:.0f}%", f"{disc_b:.0f}%", winner)

    def _add_availability_row(self, parent, row_index):
        return self._add_row(
            parent, row_index, "Availability",
            describe_availability(self.product_a), describe_availability(self.product_b),
        )

    def _add_text_row(self, parent, row_index, label, key, default="N/A", transform=None):
        value_a = self.product_a.get(key) or default
        value_b = self.product_b.get(key) or default
        if transform:
            value_a, value_b = transform(value_a), transform(value_b)
        return self._add_row(parent, row_index, label, value_a, value_b)

    # ------------------------------------------------------------------
    # Verdict summary
    # ------------------------------------------------------------------

    def _build_verdict(self):
        """
        A one-line plain-English summary using the SAME weighted score
        from Module 6, so the comparison view and the recommendation
        engine never disagree with each other about which product is
        "better overall".
        """
        score_a = self.product_a.get("score")
        score_b = self.product_b.get("score")
        title_a = self.product_a.get("title", "Product A")
        title_b = self.product_b.get("title", "Product B")

        if score_a is None or score_b is None:
            return "Overall match score not available for one or both products."
        if score_a > score_b:
            return f"Based on the recommendation engine's weighted score, \u201c{title_a}\u201d ranks higher overall ({score_a} vs {score_b})."
        elif score_b > score_a:
            return f"Based on the recommendation engine's weighted score, \u201c{title_b}\u201d ranks higher overall ({score_b} vs {score_a})."
        else:
            return "Both products have an equal overall match score."