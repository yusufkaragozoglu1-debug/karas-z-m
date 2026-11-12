"""Anonymous voter identity: a signed cookie holding a random token."""

import re
import uuid

from django.conf import settings

COOKIE_NAME = "kararsizim_voter"
COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # one year
_TOKEN_RE = re.compile(r"^[0-9a-f]{32}$")


def get_voter_token(request):
    """Return the verified token from the cookie, or '' if missing/invalid."""
    token = request.get_signed_cookie(COOKIE_NAME, default="", max_age=COOKIE_MAX_AGE)
    return token if _TOKEN_RE.match(token) else ""


def new_voter_token():
    return uuid.uuid4().hex


def set_voter_cookie(response, token):
    response.set_signed_cookie(
        COOKIE_NAME,
        token,
        max_age=COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=settings.VOTER_COOKIE_SECURE,
    )
    return response
