"""Exercise real yt-dlp downloads and ffmpeg using generated local media, not YouTube access.

python tools/verify_youtube_processing.py [--ffmpeg /path/to/ffmpeg]
"""
import argparse
import copy
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yt_dlp
from youtube_sources import download_youtube, format_choices


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ffmpeg', default=shutil.which('ffmpeg'))
    args = parser.parse_args()
    if not args.ffmpeg:
        parser.error('ffmpeg is required; pass its executable path with --ffmpeg')
    real_ydl = yt_dlp.YoutubeDL
    results = []
    with tempfile.TemporaryDirectory(prefix='postsav-youtube-fixture-') as temporary:
        root = Path(temporary)
        subprocess.run([args.ffmpeg, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=green:s=320x240:r=24',
                        '-t', '1', '-an', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(root / 'video.mp4')], check=True)
        subprocess.run([args.ffmpeg, '-v', 'error', '-f', 'lavfi', '-i', 'sine=frequency=440:sample_rate=44100',
                        '-t', '1', '-c:a', 'aac', '-b:a', '128k', str(root / 'audio.m4a')], check=True)
        server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=temporary))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            origin = f'http://127.0.0.1:{server.server_port}'
            info = dict(id='BaW_jenozKc', title='Generated test video', duration=1, extractor='youtube',
                        webpage_url='https://www.youtube.com/watch?v=BaW_jenozKc', formats=[
                            dict(format_id='v240', url=origin + '/video.mp4', ext='mp4', protocol='http',
                                 height=240, width=320, vcodec='avc1', acodec='none', filesize=(root / 'video.mp4').stat().st_size),
                            dict(format_id='a128', url=origin + '/audio.m4a', ext='m4a', protocol='http',
                                 vcodec='none', acodec='mp4a', abr=128, filesize=(root / 'audio.m4a').stat().st_size)])
            # Public extraction normally returns HTTPS formats. Fixture transport
            # is localhost HTTP; choices are built from equivalent HTTPS metadata.
            metadata = copy.deepcopy(info)
            for item in metadata['formats']:
                item['protocol'] = 'https'
            choices = format_choices(metadata, 2 * 1024 * 1024, True)
            asset = dict(youtube_options=choices)
            post = dict(url=info['webpage_url'])

            def fixture_ydl(opts):
                instance = real_ydl(opts)
                instance.extract_info = lambda _url, download=True: instance.process_ie_result(copy.deepcopy(info), download=download)
                return instance

            for choice in ['mp4-240', 'mp3-128', 'mp3-192', 'mp3-256', 'mp3-320']:
                directory = root / choice
                directory.mkdir()
                with patch('youtube_sources.yt_dlp.YoutubeDL', side_effect=fixture_ydl):
                    path, quality, mime = download_youtube(post, dict(asset, selection=choice), str(directory),
                                                          dict(quiet=True, no_warnings=True, ffmpeg_location=args.ffmpeg), 2 * 1024 * 1024, True)
                decoded = subprocess.run([args.ffmpeg, '-i', path, '-f', 'null', '-'], capture_output=True, check=True)
                diagnostics = decoded.stderr.decode('utf-8', 'replace')
                assert 'Audio:' in diagnostics, 'Missing audio stream'
                if choice.startswith('mp4'):
                    assert 'Video:' in diagnostics, 'Missing video stream'
                else:
                    assert 'Video:' not in diagnostics, 'Audio-only output unexpectedly has video'
                results.append(dict(choice=choice, bytes=Path(path).stat().st_size, mime=mime, status='PASS'))
                print(json.dumps(results[-1]), flush=True)
        finally:
            server.shutdown()
            server.server_close()
    destination = Path(__file__).resolve().parents[1] / 'docs/youtube-processing-results.json'
    destination.write_text(json.dumps(dict(source='generated localhost fixtures; not live YouTube', results=results), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
