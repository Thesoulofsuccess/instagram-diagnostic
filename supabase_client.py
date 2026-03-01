import os
import time

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass


def _get_credentials():
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_ANON_KEY"]
        return url, key
    except Exception:
        url = os.getenv("SUPABASE_URL", "")
        key = os.getenv("SUPABASE_ANON_KEY", "")
        return url, key


def _make_client(access_token: str = None, refresh_token: str = None):
    """
    Create a fresh Supabase client per call (safe for multi-user).
    Tries to use ClientOptions for longer timeouts (supabase >= 2.1);
    falls back to plain create_client for older versions like 2.0.3.
    """
    from supabase import create_client

    # ClientOptions was added in supabase-py > 2.0.x — import safely
    try:
        from supabase import ClientOptions
        _has_client_options = True
    except ImportError:
        _has_client_options = False

    url, key = _get_credentials()
    if not url or not key:
        raise ValueError(
            "SUPABASE_URL and SUPABASE_ANON_KEY must be set in "
            ".streamlit/secrets.toml or environment variables."
        )

    # Increase PostgREST timeout to 30 s — free tier projects need
    # a few seconds to wake up from sleep on the first request.
    try:
        if _has_client_options:
            options = ClientOptions(postgrest_client_timeout=30)
            client = create_client(url, key, options=options)
        else:
            client = create_client(url, key)
    except (TypeError, Exception):
        # Fall back gracefully if options aren't accepted
        client = create_client(url, key)

    if access_token and refresh_token:
        try:
            client.auth.set_session(access_token, refresh_token)
        except Exception:
            pass

    return client


def _retry(fn, attempts: int = 3, delay: float = 3.0):
    """
    Call fn() up to `attempts` times, waiting `delay` seconds between tries.
    Returns (result, None) on success or (None, last_error_string) on failure.

    This handles the Supabase free-tier 'cold start' — the first request
    after the project has been sleeping often times out; the second succeeds
    once the project is awake.
    """
    last_err = None
    for attempt in range(attempts):
        try:
            return fn(), None
        except Exception as e:
            last_err = e
            if attempt < attempts - 1:
                time.sleep(delay)
    return None, str(last_err)


# ─────────────────────────────────────────────────
# AUTH
# ─────────────────────────────────────────────────

def sign_up(email: str, password: str):
    """Register a new user. Returns (AuthResponse, None) or (None, error_str)."""
    def _do():
        client = _make_client()
        response = client.auth.sign_up({"email": email, "password": password})
        if not response.user:
            raise RuntimeError("Sign up failed — please try again.")
        return response

    result, err = _retry(_do, attempts=3, delay=3.0)
    if err:
        # Make the timeout message friendlier
        if "timed out" in err.lower() or "timeout" in err.lower():
            err = (
                "Connection timed out. Your Supabase project may be waking up "
                "from sleep — please wait 10 seconds and try again."
            )
        return None, err
    return result, None


def reset_password_email(email: str):
    """Send a Supabase password-reset email. Returns (True, None) or (False, error_str)."""
    def _do():
        client = _make_client()
        client.auth.reset_password_for_email(email)
        return True

    result, err = _retry(_do, attempts=2, delay=2.0)
    if err:
        if "timed out" in err.lower() or "timeout" in err.lower():
            err = "Connection timed out — please try again in a moment."
    return (True, None) if result else (False, err)


def sign_in(email: str, password: str):
    """Sign in an existing user. Returns (AuthResponse, None) or (None, error_str)."""
    def _do():
        client = _make_client()
        response = client.auth.sign_in_with_password(
            {"email": email, "password": password}
        )
        if not response.user:
            raise RuntimeError("Login failed — check your email and password.")
        return response

    result, err = _retry(_do, attempts=3, delay=3.0)
    if err:
        if "timed out" in err.lower() or "timeout" in err.lower():
            err = (
                "Connection timed out. Your Supabase project may be waking up "
                "from sleep — please wait 10 seconds and try again."
            )
        elif "invalid login" in err.lower():
            err = "Wrong email or password. Double-check and try again."
        return None, err
    return result, None


# ─────────────────────────────────────────────────
# DATA
# ─────────────────────────────────────────────────

def get_user_reels(user_id: str, access_token: str, refresh_token: str):
    """Fetch all reels for the current user, newest first."""
    def _do():
        client = _make_client(access_token, refresh_token)
        response = (
            client.table("reels")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return response.data

    result, err = _retry(_do, attempts=2, delay=2.0)
    return result, err


def save_reel_analysis(
    user_id: str,
    access_token: str,
    refresh_token: str,
    inputs: dict,
    results: dict,
    ai_report_text: str,
):
    """Persist a completed reel diagnostic to the `reels` table."""
    def _do():
        client = _make_client(access_token, refresh_token)
        data = {
            "user_id":               user_id,
            "category":              inputs.get("category", ""),
            "hook_type":             inputs.get("hook_type", ""),
            "hook_style":            results["hook"]["label"],
            "caption":               inputs.get("caption", ""),
            "views":                 int(inputs.get("views", 0)),
            "watch_time_minutes":    float(inputs.get("watch_time_minutes", 0)),
            "reel_duration_seconds": int(inputs.get("reel_duration_seconds", 15)),
            "likes":                 int(inputs.get("likes", 0)),
            "comments":              int(inputs.get("comments", 0)),
            "shares":                int(inputs.get("shares", 0)),
            "saves":                 int(inputs.get("saves", 0)),
            "follower_count":        int(inputs.get("follower_count", 0)),
            "retention_ratio":       float(results["retention"]["ratio"]),
            "retention_label":       results["retention"]["label"],
            "engagement_rate":       float(results["engagement"]["rate"]),
            "engagement_label":      results["engagement"]["label"],
            "hook_score":            float(results["hook"]["score"]),
            "hook_label":            results["hook"]["label"],
            "save_rate":             float(results["save_rate"]["rate"]),
            "save_label":            results["save_rate"]["label"],
            "ai_report":             ai_report_text,
        }
        client.table("reels").insert(data).execute()
        return True

    result, err = _retry(_do, attempts=2, delay=2.0)
    if err:
        return False, err
    return True, None
