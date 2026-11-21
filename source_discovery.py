"""Validate explicitly authorized direct media sources for WorldStream.

Sources must be listed in providers.json with permission confirmed by the operator.
No website scraping, iframe extraction, DRM bypass, or cookie/token capture.
"""
import json
import datetime as dt
import urllib.request
import urllib.error
from urllib.parse import urlparse

TYPES = {"video/mp4", "application/vnd.apple.mpegurl", "application/x-mpegurl", "application/dash+xml", "video/webm"}
EXTENSIONS = (".mp4", ".m3u8", ".mpd", ".webm")

def probe(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return False, "Only public HTTPS media URLs are accepted"
    # Avoid accessing local/internal hosts if a configuration is edited.
    host = parsed.hostname.lower()
    if host in ("localhost",) or host.endswith((".local", ".internal")):
        return False, "Private host is not permitted"
    headers = {"User-Agent": "WorldStreamCatalogUpdater/1.0", "Range": "bytes=0-1023"}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
            status = response.status
            final = urlparse(response.url)
            if final.scheme != "https":
                return False, "Redirected away from HTTPS"
            if status not in (200, 206):
                return False, "HTTP " + str(status)
            if mime not in TYPES and not final.path.lower().endswith(EXTENSIONS):
                return False, "Unexpected content type: " + mime
            body = response.read(4096)
            if not media_signature(body, mime):
                return False, "Response does not contain a recognized media header"
            return True, "Reachable media header; device decoding untested: HTTP " + str(status) + " " + mime
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, type(exc).__name__ + ": " + str(exc)[:120]

def media_signature(body, mime):
    stripped = body.lstrip()
    if mime in ('text/html','application/json') or stripped.lower().startswith((b'<!doctype html',b'<html')):
        return False
    return (b'ftyp' in body[:32] or body.startswith(b'\x1a\x45\xdf\xa3')
            or stripped.startswith(b'#EXTM3U') or b'<MPD' in body[:4096])

def load_sources(path="providers.json"):
    with open(path, encoding="utf-8") as file:
        config = json.load(file)
    return config.get("sources", [])

def validated_sources():
    items, report = [], []
    for source in load_sources():
        title = source.get("title", "").strip()
        url = source.get("playback_url", "").strip()
        authorized = source.get("authorized_for_third_party_playback") is True
        if not title or not url or not authorized:
            report.append({"title": title or "(unnamed)", "status": "skipped", "reason": "Missing title, URL or authorization"})
            continue
        valid, reason = probe(url)
        report.append({"title": title, "status": "reachable" if valid else "unavailable", "reason": reason})
        if not valid:
            continue
        items.append({
            "id": "provider:" + str(source.get("id", title.lower().replace(" ", "-"))),
            "type": source.get("type", "movie") if source.get("type") in ("movie", "series") else "movie",
            "title": title, "poster": source.get("poster", ""),
            "description": source.get("description", ""), "year": str(source.get("year", "")),
            "genre": source.get("genre", ""), "metadata_url": source.get("metadata_url", ""),
            "playback_url": url, "playable": True,
            "metadata_source": source.get("provider", "authorized-provider"),
            "license_note": source.get("license_note", ""),
            "authorized_for_third_party_playback": True,
            "availability": "reachable", "last_validated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "catalog_id": source.get("catalog_id"), "season": source.get("season"), "episode": source.get("episode"),
            "diagnostic": source.get("diagnostic", False), "priority": source.get("priority",100)
        })
    return items, report

