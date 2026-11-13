"""Small fixed-window rate limiter backed by Django's cache.

Production uses the database cache (shared across Vercel's serverless instances).
It is intentionally forgiving: if the cache is unavailable the request is allowed,
so a cache problem can never take the site down.
"""

import time
from functools import wraps

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import render

MESSAGE = "Çok fazla deneme yaptın. Lütfen biraz bekleyip tekrar dene."


def client_ip(request):
    # Vercel sets X-Forwarded-For to the real client address.
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


def is_limited(key, limit, window):
    """Count this hit; return True when it exceeds `limit` within `window` seconds."""
    if not getattr(settings, "RATELIMIT_ENABLED", True):
        return False
    cache_key = f"rl:{key}"
    now = time.time()
    try:
        count, started = cache.get(cache_key) or (0, now)
        if now - started >= window:
            count, started = 0, now
        count += 1
        cache.set(cache_key, (count, started), timeout=window)
    except Exception:
        return False
    return count > limit


def rate_limit(name, limit, window, by="ip", methods=("POST",)):
    """Limit `methods` requests to `limit` per `window` seconds (per IP or per user)."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.method in methods:
                if by == "user" and request.user.is_authenticated:
                    ident = f"u{request.user.pk}"
                else:
                    ident = client_ip(request)
                if is_limited(f"{name}:{ident}", limit, window):
                    return too_many_requests(request)
            return view(request, *args, **kwargs)

        return wrapper

    return decorator


def too_many_requests(request):
    if "application/json" in request.headers.get("Accept", ""):
        response = JsonResponse({"ok": False, "message": MESSAGE}, status=429)
    else:
        response = render(request, "429.html", status=429)
    response["Retry-After"] = "60"
    return response
