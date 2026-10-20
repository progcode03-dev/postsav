"""Browser smoke check with fixture metadata; does not claim live YouTube access.

Run a local server with PUBLIC_MODE=1 PORT=5058, then run this script.
"""
import json
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit
from playwright.sync_api import sync_playwright

SITE = sys.argv[1].rstrip('/') if len(sys.argv) > 1 else 'http://127.0.0.1:5058'
qualities = [2160, 1440, 1080, 720, 480, 360, 240, 144]
choices = [dict(id=f'mp4-{q}', label=f'MP4 · {q}p') for q in qualities]
choices += [dict(id=f'mp3-{q}', label=f'MP3 · {q} kbps') for q in (128, 192, 256, 320)]
data = dict(platform='youtube', uploader='Browser test fixture', title='Example quality selector', session='fixture',
            warnings=['Fixture metadata for UI testing; not a live YouTube extraction.'],
            assets=[dict(id='0', kind='video', label='Choose a format and quality', choices=choices)])

with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport=dict(width=1280, height=900))
    errors, requests = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.route('**/api/info', lambda route: route.fulfill(content_type='application/json', body=json.dumps(data)))

    def download(route):
        chosen = parse_qs(urlsplit(route.request.url).query)['format'][0]
        requests.append(chosen)
        extension = 'mp3' if chosen.startswith('mp3') else 'mp4'
        route.fulfill(content_type='audio/mpeg' if extension == 'mp3' else 'video/mp4',
                      headers={'Content-Disposition': f'attachment; filename=fixture.{extension}'}, body=b'fixture-output')

    page.route('**/api/download?*', download)
    page.goto(SITE + '/youtube-downloader', wait_until='networkidle')
    if page.get_by_role('button', name='Reject analytics', exact=True).is_visible():
        page.get_by_role('button', name='Reject analytics', exact=True).click()
    page.locator('#ack').check()
    page.locator('#url').fill('https://youtu.be/BaW_jenozKc')
    page.locator('#go').click()
    selector = page.get_by_label('YouTube format and quality')
    selector.wait_for()
    assert selector.locator('option').count() == 12
    assert not page.locator('#all').is_visible()
    for choice in ('mp4-2160', 'mp3-320'):
        selector.select_option(choice)
        with page.expect_download() as saved:
            page.get_by_role('button', name='Download selected format').click()
        assert saved.value.failure() is None
        assert saved.value.suggested_filename.endswith('.mp3' if choice.startswith('mp3') else '.mp4')
        page.wait_for_function("document.getElementById('msg').textContent.includes('Download ready')")
    assert requests == ['mp4-2160', 'mp3-320']
    assert not errors, errors
    page.locator('#result').screenshot(path='docs/youtube-selector-desktop.png')
    page.set_viewport_size(dict(width=375, height=812))
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.locator('#result').screenshot(path='docs/youtube-selector-mobile.png')
    browser.close()
print('PASS: quality selector, MP4/MP3 requests and saved filenames, no ZIP, mobile layout, no JavaScript exceptions.')
