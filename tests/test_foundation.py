import unittest
from catalog_pipeline import merge_metadata,attach_sources
from multi_source import add_sources
from source_discovery import media_signature

class FoundationTests(unittest.TestCase):
    def item(self, ident='a'):
        return {'id':ident,'type':'movie','title':ident,'playable':True,'playback_url':'https://example.org/a.mp4'}
    def source(self, **fields):
        return {'id':'provider:a','catalog_id':'a','playback_url':'https://example.org/a.mp4',
                'authorized_for_third_party_playback':True,'license_note':'fixture',
                'availability':'reachable',**fields}
    def test_partial_failure_keeps_metadata_and_removes_stale_playback(self):
        items=merge_metadata([self.item('a'),self.item('b')],[self.item('a')])
        self.assertEqual(2,len(items))
        self.assertFalse(any(i['playable'] for i in items))
    def test_repeated_ids_do_not_duplicate(self):
        self.assertEqual(1,len(merge_metadata([self.item()],[self.item()])))
    def test_exact_source_attaches(self):
        items=merge_metadata([], [self.item()])
        self.assertEqual([],attach_sources(items,add_sources([self.source()])))
        self.assertTrue(items[0]['playable'])
        self.assertEqual('untested',items[0]['playback_sources'][0]['device_compatibility'])
    def test_unknown_title_does_not_attach_by_name(self):
        items=merge_metadata([], [self.item()])
        self.assertEqual(1,len(attach_sources(items,add_sources([self.source(catalog_id='other')]))))
        self.assertFalse(items[0]['playable'])
    def test_episode_match_does_not_make_series_playable(self):
        items=merge_metadata([], [{'id':'a','type':'series','seasons':[{'number':2,'episodes':[{'number':3}]}]}])
        attach_sources(items,add_sources([self.source(season=2,episode=3)]))
        self.assertFalse(items[0]['playable'])
        self.assertTrue(items[0]['seasons'][0]['episodes'][0]['playable'])
    def test_diagnostics_stay_outside_catalog(self):
        items=merge_metadata([], [self.item()])
        attach_sources(items,add_sources([self.source(diagnostic=True)]))
        self.assertFalse(items[0]['playable'])
    def test_authorization_and_health_required(self):
        for change in [{'authorized_for_third_party_playback':False},{'license_note':''},{'availability':'unavailable'}]:
            self.assertFalse(add_sources([self.source(**change)])[0]['playable'])
    def test_html_with_mp4_extension_or_mime_is_not_video(self):
        self.assertFalse(media_signature(b'<!doctype html>error','video/mp4'))
    def test_recognized_headers_are_only_transport_evidence(self):
        self.assertTrue(media_signature(b'\x00\x00\x00\x20ftypisom','video/mp4'))
        self.assertTrue(media_signature(b'#EXTM3U\n','application/x-mpegurl'))
    def test_bad_priority_does_not_abort_refresh(self):
        self.assertTrue(add_sources([self.source(priority='bad')])[0]['playable'])

if __name__=='__main__':unittest.main()

class UpdaterIntegrationTests(unittest.TestCase):
    def test_complete_refresh_preserves_old_title_and_separates_diagnostics(self):
        import json,os,tempfile
        from pathlib import Path
        from unittest.mock import patch
        import updater
        with tempfile.TemporaryDirectory() as directory:
            previous=os.getcwd()
            try:
                os.chdir(directory);Path('public').mkdir()
                Path('public/catalog.json').write_text(json.dumps({'items':[{'id':'old','type':'movie','title':'Old','metadata_source':'tmdb'}]}))
                fresh=[{'id':'new','type':'series','title':'New','metadata_source':'tvmaze'}]
                diagnostic=FoundationTests().source(diagnostic=True)
                with patch.object(updater,'validated_sources',return_value=([diagnostic],[])),patch.object(updater,'audit',return_value={}),patch.object(updater,'movie_catalog',return_value=[]),patch.object(updater,'tvmaze_shows',return_value=fresh):
                    updater.main()
                result=json.loads(Path('public/catalog.json').read_text())
                self.assertEqual({'old','new'},{i['id'] for i in result['items']})
                self.assertEqual(0,result['playable_count'])
                self.assertEqual(0,result['device_verified_count'])
                self.assertEqual(1,json.loads(Path('public/diagnostics.json').read_text())['count'])
            finally:
                os.chdir(previous)
