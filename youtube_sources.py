"""Single public YouTube videos: server-owned format choices and bounded outputs."""
import os
import re
from urllib.parse import parse_qs, urlsplit

import yt_dlp


def safe_detail(value, url):
    detail = re.sub(r'\x1b\[[0-9;]*m', '', str(value))
    identifier = parse_qs(urlsplit(url).query).get('v', [''])[0]
    if identifier:
        detail = detail.replace(identifier, '[video]')
    detail = re.sub(r'https?://\S+', '[URL]', detail)
    detail = re.sub(r'(?:[A-Za-z]:[\\/]|/(?:app|usr|tmp|home|opt)/)\S+', '[path]', detail)
    detail = re.sub(r'(?is)\b(?:use --cookies|cookie:|authorization:|password:).*', '[redacted]', detail)
    return ' '.join(detail.split())[:400]


class DiagnosticLogger:
    def __init__(self):
        self.warnings = []

    def debug(self, _message):
        pass

    def warning(self, message):
        self.warnings.append(str(message))
        self.warnings = self.warnings[-5:]

    error = warning


class YouTubeExtractionError(ValueError):
    """A safe user message plus request-scoped diagnostics, never credentials or URLs."""
    def __init__(self, message, cause, url, warnings=(), code='youtube_extraction_failed', status=502):
        super().__init__(message)
        self.code = code
        self.status = status
        self.provider_detail = safe_detail(cause, url)
        self.provider_warnings = [safe_detail(warning, url) for warning in warnings]


def extraction_error(cause, url, warnings=(), downloading=False):
    # yt-dlp's final exception can omit the HTTP errors from its client attempts.
    # Inspect those warnings too, rather than blaming every video for a host block.
    details = '\n'.join([str(cause), *warnings]).lower()
    rate_limited = bool(re.search(r'http (?:error )?429\b|too many requests', details))
    access_blocked = bool(re.search(r'http (?:error )?403\b', details)) or any(
        phrase in details for phrase in ('not a bot', 'sign in to confirm'))
    if rate_limited or access_blocked:
        return YouTubeExtractionError(
            'YouTube is blocking or limiting requests from our server. YouTube downloads are currently unavailable here. '
            'Changing the video link will not resolve this server connection issue.',
            cause, url, warnings, code='youtube_server_blocked', status=503)
    message = ('YouTube could not provide the selected format. Fetch the video again or choose a lower quality.'
               if downloading else 'YouTube could not load this video. It may be unavailable or restricted.')
    return YouTubeExtractionError(message, cause, url, warnings)


def youtube_url(raw):
    try:
        p = urlsplit(raw.strip())
        if p.scheme not in ('http', 'https') or p.username or p.password or p.port not in (None, 80, 443):
            return None
        if p.hostname in ('youtu.be', 'www.youtu.be'):
            identifier = p.path.strip('/')
        elif p.hostname in ('youtube.com', 'www.youtube.com', 'm.youtube.com', 'music.youtube.com'):
            if p.path == '/watch':
                values = parse_qs(p.query).get('v', [])
                identifier = values[0] if len(values) == 1 else ''
            else:
                match = re.fullmatch(r'/(?:shorts|embed|live)/([A-Za-z0-9_-]{11})/?', p.path)
                identifier = match[1] if match else ''
        else:
            return None
        return f'https://www.youtube.com/watch?v={identifier}' if re.fullmatch(r'[A-Za-z0-9_-]{11}', identifier) else None
    except (ValueError, AttributeError):
        return None


def options(base_options):
    result = dict(base_options)
    # YouTube never imports local Instagram/browser login sessions.
    result.pop('cookiefile', None)
    result.pop('cookiesfrombrowser', None)
    result.update(noplaylist=True, skip_download=False, js_runtimes={'node': {}, 'deno': {}},
                  cachedir=False, extract_flat=False, format='bestvideo+bestaudio/best/bestaudio/bestvideo')
    proxy = os.environ.get('YOUTUBE_PROXY_URL', '').strip()
    if proxy:
        try:
            parsed = urlsplit(proxy)
            if (parsed.scheme not in ('http', 'https') or not parsed.hostname
                    or parsed.path not in ('', '/') or parsed.query or parsed.fragment
                    or any(ord(c) <= 32 for c in proxy) or parsed.port == 0):
                raise ValueError
        except ValueError:
            raise ValueError('The server administrator must correct YOUTUBE_PROXY_URL.') from None
        # One operator-managed connection for metadata AND media; never visitor input.
        result['proxy'] = proxy
    return result


def format_choices(data, max_file, ffmpeg):
    """Return only resolutions actually exposed; selectors never come from the user."""
    usable = [f for f in data.get('formats', []) if isinstance(f, dict)
              and re.fullmatch(r'[A-Za-z0-9_-]+', str(f.get('format_id', '')))
              and not f.get('has_drm') and f.get('url')
              and f.get('protocol', 'https') in ('https', 'http_dash_segments', 'm3u8_native', 'm3u8')]
    audio = [f for f in usable if f.get('vcodec') == 'none' and f.get('acodec') not in (None, 'none')]
    best_audio = max(audio, key=lambda f: (f.get('ext') == 'm4a', f.get('abr') or 0), default=None)
    grouped = {}
    for f in usable:
        if f.get('vcodec') in (None, 'none') or not f.get('height'):
            continue
        combined = f.get('acodec') not in (None, 'none')
        if not combined and (not ffmpeg or best_audio is None):
            continue
        if not ffmpeg and f.get('ext') != 'mp4':
            continue
        # Shorts use the short edge, so 1080 x 1920 appears as 1080p.
        resolution = int(min(f['height'], f.get('width') or f['height']))
        if resolution <= 0:
            continue
        estimated = (f.get('filesize') or f.get('filesize_approx') or 0)
        if not combined:
            estimated += best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
        if estimated > max_file:
            continue
        rank = (f.get('ext') == 'mp4', str(f.get('vcodec', '')).startswith('avc'), f.get('fps') or 0, f.get('tbr') or 0)
        if resolution not in grouped or rank > grouped[resolution][0]:
            selection = str(f['format_id']) + ('' if combined else '+' + str(best_audio['format_id']))
            grouped[resolution] = (rank, dict(format=selection, extension='mp4', label=f'MP4 · {resolution}p',
                                            resolution=resolution, estimated_bytes=estimated or None))
    choices = {f'mp4-{height}': grouped[height][1] for height in sorted(grouped, reverse=True)}
    if ffmpeg:
        audio_source = max(audio, key=lambda f: f.get('abr') or 0, default=None)
        if audio_source:
            for bitrate in (128, 192, 256, 320):
                estimate = int((data.get('duration') or 0) * bitrate * 1000 / 8)
                source_size = audio_source.get('filesize') or audio_source.get('filesize_approx') or 0
                if max(estimate, source_size) <= max_file:
                    choices[f'mp3-{bitrate}'] = dict(format=str(audio_source['format_id']), extension='mp3',
                                                    bitrate=bitrate, label=f'MP3 · {bitrate} kbps', estimated_bytes=estimate or None)
    return choices


def youtube_post(url, base_options, max_file, ffmpeg):
    diagnostic = DiagnosticLogger()
    opts = options(base_options)
    opts['logger'] = diagnostic
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            data = ydl.extract_info(url, download=False)
    except yt_dlp.utils.DownloadError as error:
        raise extraction_error(error, url, diagnostic.warnings) from error
    expected = parse_qs(urlsplit(url).query)['v'][0]
    if not data or data.get('_type') in ('playlist', 'multi_video') or data.get('id') != expected:
        raise ValueError('YouTube did not return the requested video. Paste a single video or Shorts link.')
    if data.get('is_live') or data.get('live_status') in ('is_live', 'is_upcoming', 'post_live'):
        raise ValueError('Live and upcoming streams are not supported. Try the finished, processed video later.')
    if data.get('availability') not in (None, 'public', 'unlisted') or (data.get('age_limit') or 0) >= 18:
        raise ValueError('This YouTube video is restricted. Only publicly accessible, unrestricted videos are supported.')
    choices = format_choices(data, max_file, ffmpeg)
    if not choices:
        raise ValueError('No supported formats fit the 250 MB file limit. The video may be restricted, or the server may need ffmpeg.')
    warnings = ['Only qualities exposed by YouTube and within the file limit are listed. Higher-resolution MP4 may use AV1 or VP9 and need a compatible player. MP3 conversion does not improve the source audio quality.']
    if not ffmpeg:
        warnings.append('This server has no ffmpeg: MP3 and separate video/audio formats are unavailable.')
    return dict(platform='youtube', id=expected, url=url, title=(data.get('title') or 'YouTube video')[:200],
                uploader=data.get('uploader') or '', warnings=warnings,
                assets=[dict(kind='video', source=url, youtube=True, thumbnail=data.get('thumbnail'), label='Choose a format and quality',
                             choices=[dict(id=key, label=value['label'], estimated_bytes=value['estimated_bytes']) for key, value in choices.items()],
                             youtube_options=choices)])


def download_youtube(post, asset, workdir, base_options, max_file, ffmpeg):
    choice = asset['youtube_options'].get(asset.get('selection', ''))
    if not choice:
        raise ValueError('Choose one of the available formats, or fetch the video again.')
    if not ffmpeg and (choice['extension'] == 'mp3' or '+' in choice['format']):
        raise ValueError('This format needs ffmpeg on the server.')

    def bounded_progress(_status):
        total = sum(os.path.getsize(os.path.join(workdir, f)) for f in os.listdir(workdir)
                    if os.path.isfile(os.path.join(workdir, f)))
        if total > max_file:
            raise ValueError('This selection exceeds 250 MB. Choose a lower quality or MP3 bitrate.')

    opts = options(base_options)
    diagnostic = DiagnosticLogger()
    opts['logger'] = diagnostic
    opts.update(format=choice['format'], outtmpl=os.path.join(workdir, 'youtube.%(ext)s'),
                progress_hooks=[bounded_progress], max_filesize=max_file, continuedl=False,
                merge_output_format='mp4', writethumbnail=False, writesubtitles=False)
    if choice['extension'] == 'mp3':
        opts['postprocessors'] = [dict(key='FFmpegExtractAudio', preferredcodec='mp3', preferredquality=str(choice['bitrate']))]
    elif ffmpeg:
        opts['postprocessors'] = [dict(key='FFmpegVideoRemuxer', preferedformat='mp4')]
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.extract_info(post['url'], download=True)
    except yt_dlp.utils.DownloadError as error:
        raise extraction_error(error, post['url'], diagnostic.warnings, downloading=True) from error
    path = os.path.join(workdir, 'youtube.' + choice['extension'])
    if not os.path.isfile(path) or not 0 < os.path.getsize(path) <= max_file:
        raise ValueError('The selected format could not be prepared within the file limit. Try a lower quality.')
    suffix = f"{choice['resolution']}p" if choice['extension'] == 'mp4' else f"{choice['bitrate']}kbps"
    return path, suffix, 'audio/mpeg' if choice['extension'] == 'mp3' else 'video/mp4'
