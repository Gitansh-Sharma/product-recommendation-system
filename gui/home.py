"""
gui/home.py
-----------
Module 1 — Home Screen (PLACEHOLDER VERSION)

Status:
    This is a temporary stub so that `main.py` can actually run and be
    demoed right now. It will be replaced with the full implementation
    (logo, search bar, category dropdown, price/rating filters,
    "Recommend" button) when we build out the GUI module properly.

    Nothing outside this file needs to change when that happens —
    main.py only depends on the class name `HomeScreen` and the fact
    that it's a CTkFrame, so the internals can be swapped freely.
"""

import customtkinter as ctk


class HomeScreen(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master)

        placeholder_label = ctk.CTkLabel(
            self,
            text="Product Recommendation System\n\n"
                 "Home Screen coming soon:\n"
                 "search bar, category filter, price filter,\n"
                 "rating filter, and recommend button.",
            font=("Arial", 18),
            justify="center",
        )
        placeholder_label.pack(expand=True)