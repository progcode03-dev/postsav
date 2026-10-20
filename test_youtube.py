import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import app
from limits import DownloadGate
from media_sources import allowed_url
from youtube_sources import youtube_url, format_choices, youtube_post, download_youtube, options

ID = 'BaW_jenozKc'
URL = 'https://www.youtube.com/watch?v=' + ID
MAX = 250 * 1024 * 1024


def source(identifier, height=None, **extra):
    return dict(format_id=str(identifier), url='https://media.googlevideo.com/test', protocol='https',
                height=height, width=height * 2 if height else None,
                vcodec='avc1' if height else 'none', acodec='none' if height else 'mp4a',
                ext='mp4' if height else 'm4a', filesize=100000, abr=128, **extra)


def video():
    return dict(id=ID, title='Test video', uploader='Creator', duration=10,
                thumbnail='https://i.ytimg.com/vi/' + ID + '/hqdefault.jpg',
                formats=[source(140), *[source(i, h) for i, h in enumerate((144, 240, 360, 480, 720, 1080, 1440, 2160), 200)]])


def post():
    with patch('youtube_sources.yt_dlp.YoutubeDL') as factory:
        factory.return_value.__enter__.return_value.extract_info.return_value = video()
        return youtube_post(URL, {}, MAX, True)


class UrlTests(unittest.TestCase):
    def test_supported_forms_normalize_to_one_video(self):
        for url in (URL, URL + '&list=ABC&t=30', 'https://youtu.be/' + ID + '?si=abc',
                    'https://m.youtube.com/shorts/' + ID, 'https://www.youtube.com/embed/' + ID,
                    'https://music.youtube.com/watch?v=' + ID, 'https://youtube.com/live/' + ID):
            self.assertEqual(app.clean_url(url), URL, url)

    def test_non_video_and_unsafe_urls_are_rejected(self):
        for url in ('https://youtube.com.evil.test/watch?v=' + ID, 'https://youtube.com/playlist?list=123',
                    'https://youtube.com/@author', 'https://youtu.be/a/b', URL + '&v=12345678901',
                    'https://user@youtube.com/watch?v=' + ID, 'https://youtube.com:444/watch?v=' + ID,
                    'https://youtube.com/watch?v=short', 'file:///youtube.com/watch?v=' + ID):
            self.assertIsNone(youtube_url(url), url)

    def test_thumbnail_hosts_are_platform_scoped(self):
        self.assertTrue(allowed_url('https://i.ytimg.com/vi/test/a.jpg', 'youtube'))
        self.assertFalse(allowed_url('https://i.ytimg.com.evil.test/a.jpg', 'youtube'))


class ChoiceTests(unittest.TestCase):
    def test_all_exposed_resolutions_and_audio_bitrates(self):
        choices = format_choices(video(), MAX, True)
        self.assertEqual([v['resolution'] for v in choices.values() if v['extension'] == 'mp4'], [2160, 1440, 1080, 720, 480, 360, 240, 144])
        self.assertEqual([v['bitrate'] for v in choices.values() if v['extension'] == 'mp3'], [128, 192, 256, 320])
        self.assertEqual(choices['mp4-1080']['format'], '205+140')

    def test_does_not_invent_resolutions_and_skips_drm_and_oversize(self):
        data = video()
        data['formats'] = [source(140), source(18, 360), source(22, 720)]
        data['formats'][-1]['has_drm'] = True
        choices = format_choices(data, MAX, True)
        self.assertIn('mp4-360', choices)
        self.assertNotIn('mp4-720', choices)
        self.assertNotIn('mp4-1080', choices)
        data['formats'][1]['filesize'] = MAX
        self.assertNotIn('mp4-360', format_choices(data, MAX, True))

    def test_short_edge_for_portrait(self):
        data = video()
        data['formats'][1].update(height=1920, width=1080)
        choices = format_choices(dict(data, formats=data['formats'][:2]), MAX, True)
        self.assertIn('mp4-1080', choices)
        self.assertNotIn('mp4-1920', choices)

    def test_no_ffmpeg_only_combined_mp4(self):
        data = video()
        data['formats'].append(source(18, 360))
        data['formats'][-1]['acodec'] = 'mp4a'
        choices = format_choices(data, MAX, False)
        self.assertEqual(list(choices), ['mp4-360'])
        self.assertEqual(choices['mp4-360']['format'], '18')

    def test_no_personal_cookies_or_playlist(self):
        opts = options(dict(cookiefile='private.txt', cookiesfrombrowser=('chrome',)))
        self.assertNotIn('cookiefile', opts)
        self.assertNotIn('cookiesfrombrowser', opts)
        self.assertTrue(opts['noplaylist'])
        self.assertIn('node', opts['js_runtimes'])

    def test_wrong_video_live_and_restricted_are_rejected(self):
        for change in ({'id': 'wrong'}, {'is_live': True}, {'live_status': 'is_upcoming'}, {'availability': 'private'}, {'age_limit': 18}, {'_type': 'playlist'}):
            with patch('youtube_sources.yt_dlp.YoutubeDL') as factory:
                factory.return_value.__enter__.return_value.extract_info.return_value = dict(video(), **change)
                with self.assertRaises(ValueError):
                    youtube_post(URL, {}, MAX, True)

    def test_bot_restriction_has_no_cookie_instructions(self):
        import yt_dlp
        with patch('youtube_sources.yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.extract_info.side_effect = yt_dlp.utils.DownloadError('Sign in to confirm you are not a bot. Use --cookies-from-browser.')
            with self.assertRaisesRegex(ValueError, 'limiting requests') as error:
                youtube_post(URL, {}, MAX, True)
        self.assertNotIn('cookies', str(error.exception))


class DownloadTests(unittest.TestCase):
    def test_exact_mp4_selector_and_audio_conversion_options(self):
        data = post()
        for selection, extension in [('mp4-1080', 'mp4'), ('mp3-192', 'mp3')]:
            with self.subTest(selection=selection), tempfile.TemporaryDirectory() as directory, patch('youtube_sources.yt_dlp.YoutubeDL') as factory:
                factory.return_value.__enter__.return_value.extract_info.side_effect = lambda *_a, **_k: Path(directory, 'youtube.' + extension).write_bytes(b'media')
                path, suffix, mime = download_youtube(data, dict(data['assets'][0], selection=selection), directory, {}, MAX, True)
                opts = factory.call_args.args[0]
                self.assertEqual(opts['format'], data['assets'][0]['youtube_options'][selection]['format'])
                self.assertEqual(Path(path).suffix, '.' + extension)
                self.assertEqual(mime, 'video/mp4' if extension == 'mp4' else 'audio/mpeg')
                if extension == 'mp3':
                    self.assertEqual(opts['postprocessors'][0]['preferredquality'], '192')
                else:
                    self.assertEqual(opts['postprocessors'][0]['preferedformat'], 'mp4')

    def test_partial_streams_cannot_exceed_combined_budget(self):
        data = post()
        with tempfile.TemporaryDirectory() as directory, patch('youtube_sources.yt_dlp.YoutubeDL') as factory:
            def overflow(*_a, **_k):
                Path(directory, 'video.part').write_bytes(b'x' * 11)
                factory.call_args.args[0]['progress_hooks'][0]({})
            factory.return_value.__enter__.return_value.extract_info.side_effect = overflow
            with self.assertRaisesRegex(ValueError, 'exceeds'):
                download_youtube(data, dict(data['assets'][0], selection='mp4-1080'), directory, {}, 10, True)


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.client = app.app.test_client()
        self.data = post()
        app.sessions.clear()
        app.download_gate = DownloadGate()

    def test_info_exposes_only_public_choices(self):
        with patch('app.youtube_post', return_value=self.data):
            response = self.client.post('/api/info', json={'url': URL, 'ack': True})
        self.assertEqual(response.status_code, 200)
        asset = response.json['assets'][0]
        self.assertIn('choices', asset)
        self.assertNotIn('youtube_options', asset)
        self.assertNotIn('source', asset)

    def test_forged_choices_and_zip_are_rejected_without_consuming_slot(self):
        token = app.remember(self.data)
        for args in ({'asset': 'all', 'format': 'mp4-720'}, {'asset': '0', 'format': 'best'}, {'asset': '0', 'format': 'mp4-9999'}, {'asset': '0'}):
            result = self.client.get('/api/download', query_string=dict(session=token, **args))
            self.assertEqual(result.status_code, 400)
            self.assertEqual(app.download_gate.active, 0)

    def test_selection_is_isolated_and_cleanup_runs(self):
        token = app.remember(self.data)
        seen = []
        def fake_download(data, asset, directory, *_args):
            seen.append(asset['selection'])
            path = Path(directory, 'youtube.mp3')
            path.write_bytes(b'mp3-content')
            return str(path), '192kbps', 'audio/mpeg'
        with patch('app.download_youtube', side_effect=fake_download):
            response = self.client.get('/api/download', query_string=dict(session=token, asset='0', format='mp3-192'))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data, b'mp3-content')
            self.assertIn(ID + '_192kbps.mp3', response.headers['Content-Disposition'])
            response.close()
        self.assertEqual(seen, ['mp3-192'])
        self.assertNotIn('selection', app.get_session(token)['assets'][0])
        self.assertEqual(app.download_gate.active, 0)

    def test_download_error_releases_slot(self):
        token = app.remember(self.data)
        with patch('app.download_youtube', side_effect=ValueError('Format unavailable')):
            response = self.client.get('/api/download', query_string=dict(session=token, asset='0', format='mp4-720'))
        self.assertEqual(response.status_code, 502)
        self.assertEqual(app.download_gate.active, 0)


if __name__ == '__main__':
    unittest.main()
