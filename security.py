"""Security helpers: safe redirects, URL handling, and response headers."""
import re
from urllib.parse import urlparse, urljoin

from markupsafe import Markup, escape
from flask import request


def is_safe_redirect_target(target):
    """Only allow redirects to paths on this same host (open-redirect guard)."""
    if not target:
        return False
    host_url = request.host_url
    redirect_url = urljoin(host_url, target)
    parsed_host = urlparse(host_url)
    parsed_redirect = urlparse(redirect_url)
    return (
        parsed_redirect.scheme in ("http", "https")
        and parsed_host.netloc == parsed_redirect.netloc
    )


# Matches bare http(s) URLs in free text.
_URL_RE = re.compile(r"(https?://[^\s<>\"']+)")


def is_safe_external_url(url):
    """Accept only http/https; reject javascript:, data:, etc."""
    try:
        scheme = urlparse(url).scheme.lower()
    except ValueError:
        return False
    return scheme in ("http", "https")


def linkify(text):
    """Turn http(s) URLs in *escaped* text into safe anchor tags.

    Everything is HTML-escaped first, so any markup in the stored text stays
    inert; only genuine http(s) URLs become links, and they open with
    ``rel="noopener noreferrer"``.
    """
    if text is None:
        return Markup("")
    out = []
    last = 0
    raw = str(text)
    for match in _URL_RE.finditer(raw):
        start, end = match.span()
        out.append(str(escape(raw[last:start])))
        url = match.group(1)
        if is_safe_external_url(url):
            safe_url = str(escape(url))
            out.append(
                f'<a href="{safe_url}" target="_blank" '
                f'rel="noopener noreferrer">{safe_url}</a>'
            )
        else:
            out.append(str(escape(url)))
        last = end
    out.append(str(escape(raw[last:])))
    return Markup("".join(out))


def apply_security_headers(response):
    """Attach defensive response headers.

    The CSP permits the CDNs the templates already use (Bootstrap, Font Awesome,
    Google Fonts) plus 'self'. It is intentionally compatible with the existing
    design rather than maximally strict.
    """
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    csp = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
        "https://cdnjs.cloudflare.com https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com; "
        "img-src 'self' data:; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'"
    )
    response.headers.setdefault("Content-Security-Policy", csp)
    return response
