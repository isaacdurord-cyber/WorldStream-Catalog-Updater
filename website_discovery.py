"""Conservative website integration discovery.

Reports availability of named sites and common public discovery documents.
Never scrapes video players, extracts streaming tokens, or infers redistribution rights.
"""
import datetime as dt
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

HEADERS = {"User-Agent": "WorldStreamDiscovery/1.0 (public integration audit)"}
PATHS = ("/robots.txt", "/.well-known/openapi.json", "/openapi.json")

def check(url):
    request = urllib.request.Request(url, headers=HEADERS, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=9) as response:
            # Avoid consuming full web pages.
            response.read(256)
            return {"status": "reachable", "http_status": response.status,
                    "content_type": response.headers.get("Content-Type", "").split(";")[0]}
    except urllib.error.HTTPError as exc:
        return {"status": "http_error", "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"status": "unavailable", "error_type": type(exc).__name__}

def audit(path="sites.json"):
    with open(path, encoding="utf-8") as file:
        sites = json.load(file)["sites"]
    results = []
    for site in sites:
        url = site["url"].rstrip("/")
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/"):
            results.append({"site": site["name"], "status": "invalid_site_configuration"})
            continue
        record = {"site": site["name"], "homepage": url, "homepage_check": check(url),
                  "public_documents": {}}
        for suffix in PATHS:
            record["public_documents"][suffix] = check(url + suffix)
        record["integration_status"] = "not_verified"
        record["authorized_direct_playback"] = False
        record["note"] = ("Reachability is not an API or streaming license. "
                          "Requires a documented, permitted integration to supply playable URLs.")
        results.append(record)
    return {"checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "sites": results}
