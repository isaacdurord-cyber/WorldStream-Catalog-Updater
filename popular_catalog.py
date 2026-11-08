"""Keyless TV discovery and optional TMDB-popularity movie discovery.

TVmaze offers public show-index pages. TMDB requires a server-side read token:
set TMDB_READ_TOKEN in GitHub Actions secrets, never in the Android app.
Wikidata is a best-effort CC0 movie metadata fallback when no token exists.
No metadata provider supplies movie video rights or playback streams.
"""
import concurrent.futures
import datetime
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {"User-Agent": "WorldStreamCatalogUpdater/2.0 (metadata; https://github.com/isaacdurord-cyber/WorldStream-Catalog-Updater)"}
MOVIE_TARGET = 10000
SERIES_TARGET = 10000

def get_json(url, headers=None, timeout=35, retries=2):
    request = urllib.request.Request(url, headers={**HEADERS, **(headers or {})})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                return json.load(response)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            if e.code not in (429, 500, 502, 503, 504) or attempt == retries:
                raise
        except (urllib.error.URLError, TimeoutError):
            if attempt == retries:
                raise
        time.sleep(min(8, 1.5 * (2 ** attempt)))

def remove_html(value):
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", value or ""))).strip()

def tvmaze_entry(show):
    ident = show.get("id")
    name = show.get("name", "").strip()
    if not ident or not name:
        return None
    image = show.get("image") or {}
    rating = (show.get("rating") or {}).get("average") or 0
    return {
        "id": "tvmaze:" + str(ident),
        "type": "series", "title": name,
        "poster": image.get("medium") or image.get("original") or "",
        "description": remove_html(show.get("summary", ""))[:420],
        "genre": ", ".join(show.get("genres") or []),
        "year": (show.get("premiered") or "")[:4],
        "metadata_url": show.get("url") or "",
        "playback_url": None, "playable": False, "metadata_source": "tvmaze",
        "popularity": show.get("weight") or 0, "rating": rating,
        "tvmaze_id": ident
    }

def tvmaze_last_page():
    # The TVmaze show index returns 404 beyond the last page.
    lo, hi = 0, 1024
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        try:
            data = get_json("https://api.tvmaze.com/shows?page=" + str(mid), timeout=15, retries=1)
            if data is None:
                hi = mid
            else:
                lo = mid
        except Exception:
            return None  # Avoid assuming a network error means end-of-list.
    return lo

def tvmaze_shows(limit=SERIES_TARGET):
    stored = {}
    try:
        with open("public/catalog.json", encoding="utf-8") as file:
            for obj in json.load(file).get("items", []):
                if obj.get("metadata_source") == "tvmaze":
                    stored[obj["id"]] = obj
    except (FileNotFoundError, ValueError, KeyError):
        pass
    last = tvmaze_last_page()
    # Broad historical coverage and newest shows, including recent releases.
    pages = set(range(0, min(95, (last or 100) + 1)))
    if last is not None:
        pages.update(range(max(0, last - 45), last + 1))
    errors = 0
    for num, page in enumerate(sorted(pages)):
        try:
            data = get_json("https://api.tvmaze.com/shows?page=" + str(page), timeout=25, retries=1)
            if isinstance(data, list):
                for show in data:
                    entry = tvmaze_entry(show)
                    if entry:
                        stored[entry["id"]] = entry
        except Exception as exc:
            errors += 1
            print("TVmaze page", page, "failed:", str(exc)[:120])
        if num % 15 == 0:
            print("TVmaze pages", num + 1, "/", len(pages), "entries:", len(stored))
        time.sleep(0.45)
    # Prioritize TVmaze's own popularity weight, then rating, then newer titles.
    result = sorted(stored.values(), key=lambda e: (
        float(e.get("popularity") or 0),
        float(e.get("rating") or 0),
        str(e.get("year") or "")
    ), reverse=True)
    print("TVmaze collected", len(stored), "shows; errors:", errors)
    return result[:limit]

TMDB_GENRES = {
    28:"Action",12:"Adventure",16:"Animation",35:"Comedy",80:"Crime",99:"Documentary",
    18:"Drama",10751:"Family",14:"Fantasy",36:"History",27:"Horror",10402:"Music",
    9648:"Mystery",10749:"Romance",878:"Science Fiction",10770:"TV Movie",
    53:"Thriller",10752:"War",37:"Western"
}

def tmdb_movies(token, limit=MOVIE_TARGET):
    headers = {"Authorization": "Bearer " + token, "Accept": "application/json"}
    def page(n):
        url = "https://api.themoviedb.org/3/discover/movie?" + urllib.parse.urlencode({
            "language":"en-US", "sort_by":"popularity.desc", "include_adult":"false",
            "include_video":"false", "page":n
        })
        try:
            return n, get_json(url, headers=headers, timeout=25, retries=2)
        except Exception as exc:
            print("TMDB movie page", n, "failed:", str(exc)[:140])
            return n, None
    data_by_page = {}
    max_pages = min(500, (limit + 19) // 20)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        for n, data in pool.map(page, range(1, max_pages+1)):
            if data and isinstance(data.get("results"), list):
                data_by_page[n] = data["results"]
    records = {}
    for n in sorted(data_by_page):
        for movie in data_by_page[n]:
            ident = movie.get("id")
            title = movie.get("title") or movie.get("original_title")
            if not ident or not title:
                continue
            poster = movie.get("poster_path") or ""
            genre = [TMDB_GENRES[g] for g in (movie.get("genre_ids") or []) if g in TMDB_GENRES]
            records[str(ident)] = {
                "id": "tmdb-movie-" + str(ident), "type": "movie",
                "title": title, "poster": ("https://image.tmdb.org/t/p/w342" + poster) if poster else "",
                "description": (movie.get("overview") or "")[:420],
                "genre": ", ".join(genre), "year": (movie.get("release_date") or "")[:4],
                "metadata_url": "https://www.themoviedb.org/movie/" + str(ident),
                "playback_url": None, "playable": False, "metadata_source": "tmdb",
                "popularity": movie.get("popularity", 0), "rating": movie.get("vote_average", 0)
            }
    return list(records.values())[:limit]

def wikidata_movies(limit=MOVIE_TARGET):
    # This fallback depends on WDQS availability and query time limits.
    # Exact output counts cannot be guaranteed; a token-backed TMDB import is preferred.
    records = {}
    endpoint = "https://query.wikidata.org/sparql?"
    for offset in range(0, limit, 500):
        query = '''SELECT ?film ?label ?sitelinks (SAMPLE(?date) AS ?release)
                          (SAMPLE(?image) AS ?poster) WHERE {
          ?film wdt:P31 wd:Q11424 ; wikibase:sitelinks ?sitelinks ; rdfs:label ?label .
          FILTER(LANG(?label) = "en")
          FILTER(?sitelinks >= 12)
          OPTIONAL { ?film wdt:P577 ?date. }
          OPTIONAL { ?film wdt:P18 ?image. }
        } GROUP BY ?film ?label ?sitelinks
        ORDER BY DESC(?sitelinks)
        LIMIT 500 OFFSET ''' + str(offset)
        url = endpoint + urllib.parse.urlencode({"query": query, "format": "json"})
        try:
            data = get_json(url, headers={"Accept":"application/sparql-results+json"},
                            timeout=45, retries=1)
            rows = data.get("results", {}).get("bindings", [])
            if not rows:
                break
            for row in rows:
                link = row["film"]["value"]
                ident = link.rsplit("/", 1)[-1]
                title = row["label"]["value"]
                if not ident.startswith("Q") or not title:
                    continue
                date = row.get("release", {}).get("value", "")
                image = row.get("poster", {}).get("value", "")
                records[ident] = {
                    "id": "wikidata:" + ident, "type": "movie", "title": title,
                    "poster": image if image.startswith("https://") else "",
                    "description": "", "genre": "Film", "year": date[:4],
                    "metadata_url": link,
                    "playback_url": None, "playable": False,
                    "metadata_source": "wikidata",
                    "popularity": int(row["sitelinks"]["value"])
                }
        except Exception as exc:
            print("Wikidata fallback stopped at offset", offset, ":", str(exc)[:160])
            break
        time.sleep(1)
    return list(records.values())[:limit]

def movie_catalog():
    token = os.environ.get("TMDB_READ_TOKEN", "").strip()
    if token:
        movies = tmdb_movies(token)
        if movies:
            print("TMDB imported", len(movies), "popular movies")
            return movies
        print("TMDB failed: falling back to Wikidata.")
    else:
        print("No TMDB_READ_TOKEN: trying keyless Wikidata metadata (best effort).")
    return wikidata_movies()

