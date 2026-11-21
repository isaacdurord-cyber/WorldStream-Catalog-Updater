"""Normalize explicit authorization and transport evidence; never claim device verification."""
from urllib.parse import urlparse

EXTENSIONS = {'.mp4':'video/mp4','.m3u8':'application/x-mpegURL',
              '.mpd':'application/dash+xml','.webm':'video/webm'}

def media_type(url):
    path = urlparse(url).path.lower()
    return next((mime for ext,mime in EXTENSIONS.items() if path.endswith(ext)), None)

def add_sources(items):
    for item in items:
        sources = list(item.get('playback_sources') or [])
        if item.get('playback_url'):
            sources.append({
                'url':item['playback_url'],'provider':item.get('metadata_source','unknown'),
                'priority':item.get('priority',100),'license_note':item.get('license_note',''),
                'authorized_for_third_party_playback':item.get('authorized_for_third_party_playback') is True,
                'availability':item.get('availability','unknown'),
                'last_validated_at':item.get('last_validated_at',''),
            })
        normalized = {}
        for src in sources:
            if not isinstance(src,dict):
                continue
            url = src.get('url','')
            if not isinstance(url,str):
                continue
            parsed = urlparse(url)
            if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                    or src.get('authorized_for_third_party_playback') is not True
                    or not src.get('license_note') or src.get('availability') != 'reachable'):
                continue
            try:
                priority = int(src.get('priority',100))
            except (ValueError,TypeError):
                priority = 100
            normalized[url] = {**src,'priority':priority,'mime_type':src.get('mime_type') or media_type(url),
                               'device_compatibility':'untested'}
        item['playback_sources'] = sorted(normalized.values(),key=lambda s:s['priority'])
        item['playable'] = bool(item['playback_sources'])
        item['playback_url'] = item['playback_sources'][0]['url'] if item['playable'] else None
    return items
