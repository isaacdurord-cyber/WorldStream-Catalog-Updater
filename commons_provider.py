"""Import openly licensed video files from Wikimedia Commons.

Uses the public MediaWiki API, not third-party streaming-site embeds.
Only direct MP4/WebM files with a recognizable open license are included.
"""
import json
import urllib.parse
import urllib.request
import re

API = "https://commons.wikimedia.org/w/api.php"
HEADERS = {"User-Agent": "WorldStreamCatalogUpdater/1.1 (open media discovery; contact via GitHub)"}
LICENSE_WORDS = ("creative commons", "cc by", "cc0", "public domain", "pd-")
VIDEO_MIMES = {"video/webm", "video/mp4"}

def plain(value):
    return re.sub(r"<[^>]*>", "", value or "").strip()

def commons_videos(limit=40):
    params = {
        "action": "query", "format": "json", "generator": "search",
        "gsrsearch": "filetype:video", "gsrnamespace": "6", "gsrlimit": str(min(limit, 50)),
        "prop": "imageinfo", "iiprop": "url|mime|extmetadata|size", "iiurlwidth": "640"
    }
    request = urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    items = []
    for page in (data.get("query", {}).get("pages", {}) or {}).values():
        info = (page.get("imageinfo") or [{}])[0]
        mime = info.get("mime", "").lower()
        url = info.get("url", "")
        if mime not in VIDEO_MIMES or not url.startswith("https://upload.wikimedia.org/"):
            continue
        metadata = info.get("extmetadata") or {}
        license_name = plain((metadata.get("LicenseShortName") or {}).get("value"))
        usage = plain((metadata.get("UsageTerms") or {}).get("value"))
        if not any(word in (license_name + " " + usage).lower() for word in LICENSE_WORDS):
            continue
        title = page.get("title", "").removeprefix("File:")
        title = re.sub(r"\.(webm|mp4)$", "", title, flags=re.I).replace("_", " ")
        if not title:
            continue
        items.append({
            "id": "commons:" + str(page["pageid"]), "type": "movie", "title": title,
            "poster": info.get("thumburl", ""), "description": plain((metadata.get("ImageDescription") or {}).get("value"))[:500],
            "genre": "Open media", "year": "", "metadata_url": "https://commons.wikimedia.org/wiki/" + urllib.parse.quote(page["title"].replace(" ", "_")),
            "playback_url": url, "playable": True, "metadata_source": "wikimedia-commons",
            "license_note": license_name or usage, "media_type": mime,
            "attribution": plain((metadata.get("Artist") or {}).get("value"))[:300]
        })
    return items
