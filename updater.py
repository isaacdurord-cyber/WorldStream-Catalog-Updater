#!/usr/bin/env python3
"""Build a metadata-only WorldStream catalog from public APIs.

No video streams are supplied. Sources: Apple iTunes Search API and TVMaze.
"""
import datetime as dt
import json
import os
import time
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "WorldStreamCatalogUpdater/1.0 (metadata-only)"}

def fetch(url):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=25) as response:
        return json.load(response)

def movies():
    terms = ["action", "comedy", "drama", "thriller", "animation", "science fiction"]
    entries = {}
    for term in terms:
        params = urllib.parse.urlencode({"term": term, "entity": "movie", "country": "US", "limit": 100})
        try:
            data = fetch("https://itunes.apple.com/search?" + params)
            for item in data.get("results", []):
                ident = item.get("trackId")
                title = item.get("trackName")
                if not ident or not title:
                    continue
                poster = item.get("artworkUrl100", "").replace("100x100bb", "600x600bb")
                entries[str(ident)] = {
                    "id": "itunes:" + str(ident),
                    "type": "movie",
                    "title": title,
                    "poster": poster,
                    "description": item.get("longDescription") or item.get("shortDescription") or "",
                    "genre": item.get("primaryGenreName") or "",
                    "year": (item.get("releaseDate") or "")[:4],
                    "metadata_url": item.get("trackViewUrl") or "",
                    "playback_url": None,
                    "playable": False,
                    "metadata_source": "itunes"
                }
        except Exception as exc:
            print("iTunes query failed:", term, str(exc))
        time.sleep(0.25)
    return list(entries.values())

def shows():
    entries = {}
    for page in (0, 1):
        try:
            data = fetch("https://api.tvmaze.com/shows?page=" + str(page))
            for show in data:
                ident, title = show.get("id"), show.get("name")
                if not ident or not title:
                    continue
                image = show.get("image") or {}
                entries[str(ident)] = {
                    "id": "tvmaze:" + str(ident),
                    "type": "series",
                    "title": title,
                    "poster": image.get("original") or image.get("medium") or "",
                    "description": "",
                    "genre": ", ".join(show.get("genres") or []),
                    "year": (show.get("premiered") or "")[:4],
                    "metadata_url": show.get("url") or "",
                    "playback_url": None,
                    "playable": False,
                    "metadata_source": "tvmaze"
                }
        except Exception as exc:
            print("TVMaze page failed:", page, str(exc))
        time.sleep(0.25)
    return list(entries.values())

def main():
    items = movies() + shows()
    if not items:
        raise SystemExit("No metadata retrieved; keeping existing catalog")
    result = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "catalog_type": "metadata_only",
        "notice": "Titles are not playable. This feed contains no licensed video streams.",
        "count": len(items),
        "items": items
    }
    os.makedirs("public", exist_ok=True)
    temp = "public/catalog.json.tmp"
    with open(temp, "w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)
    os.replace(temp, "public/catalog.json")
    print("Wrote", len(items), "metadata entries")

if __name__ == "__main__":
    main()
