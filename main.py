"""
main.py
-------
Application entry point.
 
Responsibility:
    This file's ONLY job is to configure the root window/theme and
    launch the Home Screen (gui/home.py). It intentionally contains
    NO business logic (no API calls, no filtering, no scoring) —
    that separation is what lets us unit-test recommendation logic
    without ever opening a GUI window.
 
Design decision:
    We use CustomTkinter instead of plain Tkinter because the MVP
    doc lists "Tkinter / CustomTkinter" as an either/or choice.
    CustomTkinter gives a modern, pre-themed look (rounded buttons,
    dark/light mode) with almost the same API as Tkinter, which
    saves styling work for a solo student project while still being
    easy to explain to examiners as "it's Tkinter under the hood".
"""
 
import sys
import customtkinter as ctk
 
from gui.home import HomeScreen
 
 
def main():
    # Appearance settings — applied globally before any window is created
    ctk.set_appearance_mode("System")       # "System", "Dark", or "Light"
    ctk.set_default_color_theme("blue")     # built-in CustomTkinter theme
 
    root = ctk.CTk()
    root.title("Product Recommendation System")
    root.geometry("1100x700")
    root.minsize(900, 600)
 
    # HomeScreen is a Frame subclass that builds the search bar,
    # category dropdown, price/rating filters, and recommend button
    # (Module 1 in the MVP doc). It is responsible for its own layout;
    # main.py just mounts it into the root window.
    home_screen = HomeScreen(master=root)
    home_screen.pack(fill="both", expand=True)
 
    root.mainloop()
 
 
if __name__ == "__main__":
    try:
        main()
    except ImportError as e:
        # Friendly message if dependencies aren't installed yet,
        # rather than a raw traceback.
        print("Missing dependency:", e)
        print("Run: pip install -r requirements.txt")
        sys.exit(1)
