"""Fetch each venue's own hero image from its own website.

Restaurants publish an Open Graph image for exactly this purpose — it is the
photo they want shown when their page is shared — so it is both the most
accurate picture of the room and the most defensible one to display.

This runs on the deployed server, not in the browser: the page only ever sees
the resulting URL.
"""
import gzip
import ipaddress
import re
import socket
import urllib.error
import urllib.parse
import urllib.request

UA = 'Mozilla/5.0 (compatible; venue-rfp-tool/1.0; +cover-image-fetch)'
TIMEOUT = 12
MAX_BYTES = 600_000          # hero images live in the <head>; no need for more

_META = re.compile(
    rb'<meta[^>]+(?:property|name)\s*=\s*["\']'
    rb'(og:image(?::secure_url)?|twitter:image(?::src)?)["\'][^>]*>',
    re.I)
_CONTENT = re.compile(rb'content\s*=\s*["\']([^"\']+)["\']', re.I)
_LINK_IMG = re.compile(rb'<link[^>]+rel=["\']image_src["\'][^>]+href=["\']([^"\']+)["\']', re.I)


class CoverError(Exception):
    pass


def _safe_host(url):
    """Refuse anything that is not public http(s) — these URLs are data, and a
    server-side fetcher should never be pointed at internal addresses."""
    parts = urllib.parse.urlparse(url)
    if parts.scheme not in ('http', 'https'):
        raise CoverError(f'unsupported scheme: {parts.scheme or "none"}')
    if not parts.hostname:
        raise CoverError('no host in URL')
    try:
        infos = socket.getaddrinfo(parts.hostname, None)
    except socket.gaierror as exc:
        raise CoverError(f'DNS lookup failed: {exc}')
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved:
            raise CoverError('refusing to fetch a private address')
    return parts


def _get(url):
    _safe_host(url)
    req = urllib.request.Request(url, headers={
        'User-Agent': UA,
        'Accept': 'text/html,application/xhtml+xml',
        'Accept-Encoding': 'gzip',
    })
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        raw = resp.read(MAX_BYTES)
        if resp.headers.get('Content-Encoding') == 'gzip':
            try:
                raw = gzip.decompress(raw)
            except (OSError, EOFError):
                pass                      # truncated gzip — parse what we have
        return raw, resp.geturl()


def extract_image(html, base_url):
    """Pull the page's declared share image out of its markup."""
    candidates = []
    for tag in _META.finditer(html):
        m = _CONTENT.search(tag.group(0))
        if m:
            candidates.append(m.group(1))
    m = _LINK_IMG.search(html)
    if m:
        candidates.append(m.group(1))

    for raw in candidates:
        url = raw.decode('utf-8', 'ignore').strip()
        url = url.replace('&amp;', '&')
        if not url or url.startswith('data:'):
            continue
        url = urllib.parse.urljoin(base_url, url)
        if urllib.parse.urlparse(url).scheme in ('http', 'https'):
            return url
    return ''


def fetch_cover(website):
    """Return an image URL for a venue's site, or raise CoverError.

    Tries the page given, then the site root — deep event pages are often
    thinner on metadata than the homepage.
    """
    if not website:
        raise CoverError('no website on record')

    tried, last = [], None
    parts = urllib.parse.urlparse(website)
    root = f'{parts.scheme}://{parts.netloc}/'
    for url in (website, root):
        if url in tried:
            continue
        tried.append(url)
        try:
            html, final = _get(url)
        except CoverError:
            raise
        except (urllib.error.URLError, urllib.error.HTTPError, socket.timeout, OSError) as exc:
            last = f'{type(exc).__name__}: {exc}'
            continue
        image = extract_image(html, final)
        if image:
            return image
        last = 'no og:image or twitter:image on the page'

    raise CoverError(last or 'nothing to fetch')
