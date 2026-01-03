
# broker_routes.py

import os
import logging
import json
from urllib.parse import quote_plus
from typing import Optional
from fastapi import BackgroundTasks
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse, Response, HTMLResponse

# Import your kite client wrapper and config values
# Adjust these imports to match your project structure.
from app.kite_client import kite_client  # should exist in your project
from app.config import KITE_API_KEY as CFG_API_KEY, KITE_API_SECRET as CFG_API_SECRET

log = logging.getLogger("app.broker_routes")
router = APIRouter(prefix="/brokers", tags=["brokers"])

# -------------------------------------------------------------------
# Configuration & sane defaults
# -------------------------------------------------------------------
KITE_API_KEY = (os.getenv("KITE_API_KEY") or CFG_API_KEY or "").strip()
KITE_API_SECRET = (os.getenv("KITE_API_SECRET") or CFG_API_SECRET or "").strip()

KITE_REDIRECT_URL = (
    os.getenv("KITE_REDIRECT_URL")
    or os.getenv("KITE_REDIRECT")
    or "http://127.0.0.1:8000/api/brokers/callback"
).strip()

FRONTEND_AFTER_LOGIN = (
    os.getenv("FRONTEND_REDIRECT_AFTER_LOGIN")
    or "http://localhost:5173/dashboard?login=success"
).strip()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def _get_access_token_from_kite_client() -> Optional[str]:
    """
    Try to read an access token from kite_client in multiple common shapes.
    Returns token string or None.
    """
    try:
        if kite_client is None:
            return None

        # direct attribute on wrapper
        if hasattr(kite_client, "access_token") and getattr(kite_client, "access_token"):
            return getattr(kite_client, "access_token")

        # wrapper getter method
        get_fn = getattr(kite_client, "get_access_token", None)
        if callable(get_fn):
            try:
                t = get_fn()
                if t:
                    return t
            except Exception:
                log.debug("kite_client.get_access_token() raised", exc_info=True)

        # nested / official sdk object
        kite_obj = getattr(kite_client, "kite", None)
        if kite_obj is not None:
            # kite.access_token
            if hasattr(kite_obj, "access_token") and getattr(kite_obj, "access_token"):
                return getattr(kite_obj, "access_token")
            # other possible token-like attributes
            for attr in ("token", "public_token", "api_key"):
                if hasattr(kite_obj, attr):
                    val = getattr(kite_obj, attr)
                    if val:
                        return val
            # kite_obj.get_access_token()
            get2 = getattr(kite_obj, "get_access_token", None)
            if callable(get2):
                try:
                    t = get2()
                    if t:
                        return t
                except Exception:
                    log.debug("kite_obj.get_access_token() raised", exc_info=True)
    except Exception:
        log.exception("Error reading access token from kite_client")
    return None




def popup_success_response(provider: str = "zerodha", extra: Optional[dict] = None) -> Response:
    payload = {"broker": provider, "status": "success", "extra": extra or {}}
    json_payload = json.dumps(payload)
    provider_js = json.dumps(provider)

    html = f"""
    <!doctype html>
    <html>
      <head>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width,initial-scale=1"/>
        <title>Login successful</title>
        <style>
          body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,Arial;
               background:#071019;color:#e6eef6;margin:0;
               display:flex;align-items:center;justify-content:center;height:100vh}}
          .card{{background:#071622;padding:22px;border-radius:12px;
                 box-shadow:0 12px 30px rgba(0,0,0,0.6);
                 width:320px;text-align:center}}
          h2{{margin:0 0 8px 0;font-size:18px}}
          p{{margin:0 0 18px 0;color:#93a3b8;font-size:14px}}
          button{{padding:10px 16px;border-radius:8px;border:none;
                  background:#06b6d4;color:#001;font-weight:700;cursor:pointer}}
          small{{display:block;margin-top:10px;color:#7b848c;font-size:12px}}
        </style>
      </head>
      <body>
        <div class="card" role="dialog" aria-modal="true">
          <h2>Login successful</h2>
          <p>You have successfully connected to the broker.</p>
          <button id="okBtn">OK</button>
          <small>You can close this window.</small>
        </div>

        <script>
          (function(){{
            var provider = {provider_js};
            var payload = {json_payload};

            function notifyAndClose() {{
              try {{
                localStorage.setItem("broker_login_" + provider, "success");
                localStorage.setItem(provider + "_login", "success");
                localStorage.setItem("kite_login", "success");
              }} catch (e) {{}}

              try {{
                if (window.opener && !window.opener.closed) {{
                  window.opener.postMessage(payload, "*");
                }} else if (window.parent && window.parent !== window) {{
                  window.parent.postMessage(payload, "*");
                }}
              }} catch (e) {{}}

              // 🔥 IMMEDIATE close (no delay)
              try {{ window.close(); }} catch(e) {{}}
            }}

            var ok = document.getElementById("okBtn");
            if (ok) {{
              ok.addEventListener("click", notifyAndClose);
            }}
          }})();
        </script>
      </body>
    </html>
    """
    return Response(content=html, media_type="text/html")


# -------------------------------------------------------------------
# Start login flow
# GET /start?provider=zerodha
# -------------------------------------------------------------------
@router.get("/start")
def start(provider: str = "zerodha"):
    """
    Redirect user to Zerodha login (connect).
    """
    if provider.lower() != "zerodha":
        raise HTTPException(status_code=400, detail="Only 'zerodha' provider is supported")

    if not KITE_API_KEY:
        log.error("KITE_API_KEY missing; cannot start Zerodha login")
        return JSONResponse(status_code=500, content={"ok": False, "message": "KITE_API_KEY not configured on server"})

    login_url = (
        "https://kite.zerodha.com/connect/login?v=3"
        f"&api_key={quote_plus(KITE_API_KEY)}"
        f"&redirect_url={quote_plus(KITE_REDIRECT_URL)}"
    )

    log.info("Redirecting to Zerodha login: %s", login_url)
    return RedirectResponse(url=login_url, status_code=307)


# -------------------------------------------------------------------
# Callback - exchange request_token for session
# -------------------------------------------------------------------


@router.get("/callback")
async def callback(request: Request):
    qp = request.query_params
    request_token = qp.get("request_token")
    status = qp.get("status")

    if status != "success" or not request_token:
        raise HTTPException(400, "Zerodha login failed")

    user_id = 1
    user_email = "upesian123@gmail.com"

    session = kite_client.generate_and_store_token(
        request_token=request_token,
        user_id=user_id,
        user_email=user_email,
    )

    log.info("Zerodha connected & token stored")

    # ❌ DO NOT LOAD INSTRUMENTS HERE
    return popup_success_response(
        provider="zerodha",
        extra={"token_preview": session["access_token"][:6]},
    )


# -------------------------------------------------------------------
# Status endpoint
# -------------------------------------------------------------------
@router.get("/status")
def broker_status():
    """
    Return lightweight broker/kite connection status for the frontend.
    Tries multiple ways to read a token from kite_client.
    """
    try:
        token = _get_access_token_from_kite_client()
        connected = bool(token)
        token_preview = (token[:6] + "...") if token else None
        return {
            "ok": True,
            "connected": connected,
            "api_key_loaded": bool(KITE_API_KEY),
            "redirect_url": KITE_REDIRECT_URL,
            "token_preview": token_preview,
        }
    except Exception:
        log.exception("broker_status read failed")
        return {"ok": False, "connected": False, "api_key_loaded": bool(KITE_API_KEY)}


# -------------------------------------------------------------------
# Profile endpoint (calls kite.profile() if token present)
# -------------------------------------------------------------------
@router.get("/profile")
def profile():
    if kite_client is None:
        raise HTTPException(status_code=500, detail="Server not configured with kite_client")

    token = _get_access_token_from_kite_client()
    if not token:
        raise HTTPException(status_code=401, detail="Not logged in with broker")

    kite_obj = getattr(kite_client, "kite", None)
    if kite_obj is None:
        raise HTTPException(status_code=500, detail="kite_client.kite is not available")

    try:
        profile_data = kite_obj.profile()
        return {"ok": True, "profile": profile_data}
    except Exception as exc:
        log.exception("Failed to fetch profile from kite: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to fetch profile from broker")



@router.post("/admin/load-instruments")
def admin_load_instruments(background_tasks: BackgroundTasks):
    background_tasks.add_task(kite_client.load_and_store_instruments)
    return {
        "ok": True,
        "message": "Zerodha instruments loading started in background"
    }
