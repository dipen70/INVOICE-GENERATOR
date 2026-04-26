"""
Google OAuth login + signer profile (name, email, position).

Flow:
  1. Read client_secret.json from this folder.
  2. Run InstalledAppFlow.run_local_server() — opens the browser,
     spins a tiny localhost server, captures the OAuth redirect.
  3. Hit Google's userinfo endpoint with the access token to get
     name/email/picture.
  4. Cache the credentials in ~/.invoice_app/token.json so the user
     doesn't have to log in every launch.
  5. Position/title is asked once after first login and stored in
     ~/.invoice_app/profile.json keyed by Google user id.
"""
from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, simpledialog, ttk
from typing import Optional

APP_DIR = Path.home() / ".invoice_app"
TOKEN_FILE = APP_DIR / "token.json"
PROFILE_FILE = APP_DIR / "profile.json"
CLIENT_SECRET_FILE = Path(__file__).parent / "client_secret.json"

SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]
USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def _ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def _load_profiles() -> dict:
    if not PROFILE_FILE.exists():
        return {}
    try:
        return json.loads(PROFILE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_profile(sub: str, position: str) -> None:
    _ensure_app_dir()
    profiles = _load_profiles()
    profiles[sub] = {"position": position}
    PROFILE_FILE.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


def _load_cached_creds():
    """Return google.oauth2.credentials.Credentials or None."""
    if not TOKEN_FILE.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        return Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    except Exception:
        return None


def _save_creds(creds) -> None:
    _ensure_app_dir()
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")


def _refresh_if_needed(creds):
    """If creds expired but have a refresh token, refresh in place. Returns
    True on success, False if we need a fresh login."""
    from google.auth.transport.requests import Request
    if not creds:
        return False
    if creds.valid:
        return True
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_creds(creds)
            return True
        except Exception:
            return False
    return False


def _run_oauth_flow():
    """Returns Credentials or raises."""
    if not CLIENT_SECRET_FILE.exists():
        raise FileNotFoundError(
            f"Missing {CLIENT_SECRET_FILE.name}. Place your Google OAuth "
            f"client JSON at:\n{CLIENT_SECRET_FILE}"
        )
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_secrets_file(
        str(CLIENT_SECRET_FILE), SCOPES
    )
    creds = flow.run_local_server(
        port=0,
        prompt="select_account",
        success_message="Signed in. You can close this tab.",
        open_browser=True,
    )
    _save_creds(creds)
    return creds


def _fetch_userinfo(creds) -> dict:
    """Returns {sub, email, name, given_name, picture}."""
    import requests
    resp = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {creds.token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _prompt_position(parent: tk.Misc | None, name: str,
                     current: Optional[str]) -> Optional[str]:
    """Modal dialog asking for the signer's position/title.
    Returns the entered string, or None if cancelled."""
    title = "Your Position"
    prompt = (
        f"Hi {name.split()[0] if name else ''}!\n\n"
        f"What's your position / job title at the company?\n"
        f"(e.g. Accountant, Founder, Sales Lead — appears on the invoice.)"
    )
    return simpledialog.askstring(
        title, prompt,
        initialvalue=current or "",
        parent=parent,
    )


def get_signer(parent: tk.Misc | None = None,
               force_login: bool = False) -> Optional[dict]:
    """Returns {sub, email, name, picture, position} or None if user
    cancels. Reuses cached token if possible.

    Pops a modal dialog the first time a given Google account signs in to
    capture the position/title."""
    creds = None if force_login else _load_cached_creds()

    if not _refresh_if_needed(creds):
        try:
            creds = _run_oauth_flow()
        except FileNotFoundError as exc:
            messagebox.showerror("Setup Required", str(exc), parent=parent)
            return None
        except Exception as exc:
            messagebox.showerror(
                "Login Failed",
                f"Could not complete Google sign-in:\n\n{exc}",
                parent=parent,
            )
            return None

    try:
        info = _fetch_userinfo(creds)
    except Exception as exc:
        messagebox.showerror(
            "Login Failed",
            f"Signed in, but couldn't read your Google profile:\n\n{exc}",
            parent=parent,
        )
        return None

    sub = info.get("sub", "")
    name = info.get("name", "")
    email = info.get("email", "")
    picture = info.get("picture", "")

    profiles = _load_profiles()
    cached = profiles.get(sub, {})
    position = cached.get("position")

    if not position:
        position = _prompt_position(parent, name, position)
        if not position:
            return None
        position = position.strip()
        _save_profile(sub, position)

    return {
        "sub": sub,
        "name": name,
        "email": email,
        "picture": picture,
        "position": position,
    }


def update_position(parent: tk.Misc | None, signer: dict) -> Optional[str]:
    """Modal-prompt for a new position. Updates the cache in place and
    returns the new value, or None if cancelled."""
    new_pos = _prompt_position(parent, signer.get("name", ""),
                                signer.get("position", ""))
    if not new_pos:
        return None
    new_pos = new_pos.strip()
    signer["position"] = new_pos
    _save_profile(signer["sub"], new_pos)
    return new_pos


def logout() -> None:
    """Delete the cached token. Position cache is kept (keyed by user id),
    so the next login for the same account skips the position prompt."""
    if TOKEN_FILE.exists():
        try:
            TOKEN_FILE.unlink()
        except OSError:
            pass


def login_screen(on_success) -> None:
    """Show a small login window. On successful sign-in, calls
    on_success(signer_dict). The window auto-closes."""
    win = tk.Tk()
    win.title("Invoice Generator — Sign in")
    win.geometry("420x280")
    win.configure(bg="#f0f4f8")
    win.resizable(False, False)

    tk.Label(
        win, text="Invoice Generator", bg="#f0f4f8", fg="#2c3e50",
        font=("Segoe UI", 18, "bold"),
    ).pack(pady=(40, 4))

    tk.Label(
        win, text="Sign in with Google to continue",
        bg="#f0f4f8", fg="#7f8c8d", font=("Segoe UI", 10),
    ).pack(pady=(0, 24))

    status = tk.Label(win, text="", bg="#f0f4f8", fg="#7f8c8d",
                      font=("Segoe UI", 9))
    status.pack(pady=(8, 0))

    def do_login():
        btn.config(state="disabled", text="Opening browser…")
        status.config(text="A browser window will open. Sign in there.")
        win.update_idletasks()
        signer = get_signer(parent=win)
        if signer is None:
            btn.config(state="normal", text="Sign in with Google")
            status.config(text="Sign-in cancelled.")
            return
        win.destroy()
        on_success(signer)

    btn = tk.Button(
        win, text="Sign in with Google",
        bg="#2980b9", fg="white", font=("Segoe UI", 11, "bold"),
        relief="flat", padx=18, pady=10, cursor="hand2",
        command=do_login,
    )
    btn.pack()

    win.mainloop()
