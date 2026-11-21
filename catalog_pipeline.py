"""Catalog reconciliation. Metadata never establishes playback availability."""
from copy import deepcopy

def merge_metadata(old, fresh):
    """Preserve missing records on partial provider failure; clear stale stream claims.

    Removal is deliberately explicit: future provider tombstones can implement deletion.
    Refreshes with different provider IDs are not guessed to be the same title.
    """
    merged = {}
    for item in list(old) + list(fresh):
        if not isinstance(item, dict) or item.get('type') not in ('movie', 'series') or not item.get('id'):
            continue
        if item.get('diagnostic') or item.get('metadata_source') in ('wikimedia-commons','MDN','mdn-test-video'):
            continue
        merged[item['id']] = deepcopy(item)
    def clear(item):
        item['playback_url'] = None
        item['playback_sources'] = []
        item['playable'] = False
        for season in item.get('seasons', []):
            for episode in season.get('episodes', []):
                clear(episode)
    for item in merged.values():
        clear(item)
    return list(merged.values())

def attach_sources(items, source_items):
    """Only exact provider-approved title IDs and episode coordinates can match."""
    by_id = {item['id']: item for item in items}
    unmatched = []
    for source in source_items:
        if source.get('diagnostic'):
            continue
        ident = source.get('catalog_id')
        target = by_id.get(ident)
        if target is not None and target.get('type') == 'series':
            target = next((e for s in target.get('seasons', [])
                           if s.get('number') == source.get('season')
                           for e in s.get('episodes', [])
                           if e.get('number') == source.get('episode')), None)
        if target is None:
            unmatched.append({'source_id': source.get('id'), 'catalog_id': ident,
                              'reason': 'No exact catalog title/episode match'})
            continue
        for entry in source.get('playback_sources', []):
            if (entry.get('authorized_for_third_party_playback') is True
                    and entry.get('availability') == 'reachable' and entry.get('license_note')):
                target.setdefault('playback_sources', []).append(deepcopy(entry))
        unique = {s['url']: s for s in target.get('playback_sources', [])}
        target['playback_sources'] = sorted(unique.values(), key=lambda s:s.get('priority',100))
        target['playable'] = bool(target['playback_sources'])
        target['playback_url'] = target['playback_sources'][0]['url'] if target['playable'] else None
    return unmatched
