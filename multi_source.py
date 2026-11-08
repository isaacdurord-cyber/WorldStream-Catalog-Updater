"""Normalize multiple authorized direct media sources for the Android TV client."""
from urllib.parse import urlparse

EXTENSIONS = {".mp4": "video/mp4", ".m3u8": "application/x-mpegURL",
              ".mpd": "application/dash+xml", ".webm": "video/webm"}

def media_type(url):
    path = urlparse(url).path.lower()
    for suffix, mime in EXTENSIONS.items():
        if path.endswith(suffix):
            return mime
    return None

def add_sources(items):
    for item in items:
        urls = []
        if item.get("playback_url"):
            urls.append({"url": item["playback_url"], "provider": item.get("metadata_source", "unknown"),
                         "license_note": item.get("license_note", ""), "priority": 1})
        for src in item.get("playback_sources", []):
            if isinstance(src, dict):
                urls.append(src)
        unique = set()
        normalized = []
        for src in urls:
            url = src.get("url", "")
            parsed = urlparse(url)
            if parsed.scheme != "https" or not parsed.netloc or url in unique:
                continue
            unique.add(url)
            normalized.append({"url": url, "provider": src.get("provider", "authorized-provider"),
                               "mime_type": src.get("mime_type") or media_type(url),
                               "priority": int(src.get("priority", 100)),
                               "license_note": src.get("license_note", "")})
        normalized.sort(key=lambda s: s["priority"])
        item["playback_sources"] = normalized
        item["playable"] = bool(normalized) and bool(item.get("playable"))
        # Backward compatibility for existing Android TV clients.
        item["playback_url"] = normalized[0]["url"] if item["playable"] else None
    return items
