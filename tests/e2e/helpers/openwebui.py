"""open-webui auth helper.

open-webui gates its `/ollama/*` and `/api/*` routes behind a bearer token even
when WEBUI_AUTH=False. In that mode a `signin` with any credentials
auto-authenticates as the default admin (admin@localhost), is idempotent, and
creates no persistent user — so we sign in, never sign up. (Signing up would
create a real user, which puts WEBUI_AUTH=False into a broken state where signin
then returns 400 "can't turn off auth with existing users".)

signup is kept only as a fallback for WEBUI_AUTH=True installs with no user yet.
"""

from __future__ import annotations

import httpx

_EMAIL = "e2e@moai.test"
_PASSWORD = "e2e-passw0rd"
_NAME = "e2e"


class OpenWebUIAuthError(RuntimeError):
    pass


def auth_token(base_url: str, *, timeout_s: float = 30.0) -> str:
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_s) as c:
        # WEBUI_AUTH=False: auto-login as default admin (idempotent, no user
        # created). WEBUI_AUTH=True: signs in an already-existing user.
        signin = c.post(
            "/api/v1/auths/signin",
            json={"email": _EMAIL, "password": _PASSWORD},
        )
        if signin.status_code == 200:
            return signin.json()["token"]
        # WEBUI_AUTH=True with no user yet — create the first (admin) user.
        signup = c.post(
            "/api/v1/auths/signup",
            json={"name": _NAME, "email": _EMAIL, "password": _PASSWORD},
        )
        if signup.status_code == 200:
            return signup.json()["token"]
    raise OpenWebUIAuthError(
        f"could not obtain an open-webui token "
        f"(signin {signin.status_code}, signup {signup.status_code}). "
        "Expected WEBUI_AUTH=False (auto-login) on a volume with no manually "
        "created users."
    )
