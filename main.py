import tkinter as tk

from ui import build_ui


if __name__ == "__main__":
    root = tk.Tk()
    build_ui(root)
    root.mainloop()
