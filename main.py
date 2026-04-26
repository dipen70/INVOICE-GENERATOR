import tkinter as tk

from auth import login_screen
from ui import build_ui


def _start_app(signer):
    root = tk.Tk()
    build_ui(root, signer)
    root.mainloop()


if __name__ == "__main__":
    login_screen(on_success=_start_app)
