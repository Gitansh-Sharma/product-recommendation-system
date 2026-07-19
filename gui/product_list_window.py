"""
gui/product_list_window.py
----------------------------
Shared popup window that displays a grid of ProductCards from a plain
list of products — used by BOTH Module 9 (Wishlist) and Module 10
(Recently Viewed), since they're structurally the same screen (a
titled grid of saved products) with only the data source differing.

Design decision:
    Rather than writing gui/wishlist.py and gui/recently_viewed.py as
    two near-identical files (each rebuilding a scrollable card grid
    from scratch), one shared, parameterized window class serves both.
    This is the same "don't repeat the grid-rendering logic" principle
    already applied with ProductCard itself being reused across the
    results list and this window.
"""

import customtkinter as ctk

from gui.product_card import ProductCard
from gui.details import ProductDetailsWindow

CARDS_PER_ROW = 4


class ProductListWindow(ctk.CTkToplevel):
    """
    A popup window showing a titled grid of products, with an optional
    empty-state message when the list is empty.

    `products`: list of normalized product dicts to display.
    `window_title`: shown in the window's title bar and as a heading.
    `empty_message`: shown instead of a grid when `products` is empty.
    """

    def __init__(self, master, products, window_title, empty_message):
        super().__init__(master)
        self.products = products

        self.title(window_title)
        self.geometry("980x650")
        self.minsize(600, 400)
        self.transient(master)
        self.grab_set()

        header = ctk.CTkLabel(self, text=window_title, font=("Arial", 18, "bold"))
        header.pack(pady=(15, 10))

        if not products:
            ctk.CTkLabel(self, text=empty_message, font=("Arial", 13), text_color="gray60").pack(pady=40)
            return

        scroll_frame = ctk.CTkScrollableFrame(self)
        scroll_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        for index, product in enumerate(products):
            row, col = divmod(index, CARDS_PER_ROW)
            card = ProductCard(scroll_frame, product, on_click=self._on_card_clicked)
            card.grid(row=row, column=col, padx=10, pady=10)

    def _on_card_clicked(self, product):
        ProductDetailsWindow(self, product)