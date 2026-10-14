from pathlib import Path
import json
import sys
SITE = sys.argv[1].rstrip('/') if len(sys.argv)>1 else 'http://127.0.0.1:5058'
import io
from PIL import Image
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(headless=True,channel='msedge')
 page=browser.new_page(viewport={'width':1440,'height':1000},device_scale_factor=1)
 errors=[];page.on('pageerror',lambda e: errors.append(str(e)))
 page.goto(SITE+'/',wait_until='networkidle')
 page.screenshot(path='docs/redesign-desktop.png',full_page=True)
 page.screenshot(path='docs/redesign-desktop-top.png')
 assert page.locator('h1').count()==1
 assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
 assert not page.locator('script[src*="googletagmanager.com"]').count()
 page.get_by_role('button',name='Reject analytics',exact=True).click()
 page.locator('#url').fill('https://example.com')
 page.locator('#ack').check();page.locator('#go').click()
 page.wait_for_function("document.getElementById('msg').className === 'err'")
 print('Invalid URL message:',page.locator('#msg').inner_text())
 for path in ['/linkedin-downloader','/pinterest-downloader','/instagram-downloader','/about','/privacy','/contact']:
  page.goto(SITE+path,wait_until='networkidle')
  assert page.locator('h1').count()==1,path
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),path
 page.set_viewport_size({'width':375,'height':812})
 for path in ['/','/linkedin-downloader','/privacy']:
  page.goto(SITE+path,wait_until='networkidle')
  assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'),path
  if path=='/':
   page.screenshot(path='docs/redesign-mobile-top.png')
   for y in range(0, page.evaluate('document.body.scrollHeight'), 650):
    page.evaluate('(y) => window.scrollTo(0,y)', y); page.wait_for_timeout(150)
   page.screenshot(path='docs/redesign-mobile.png',full_page=True)
 page.locator('.menu summary').click();assert page.locator('.menu-panel').is_visible()
 page.goto(SITE+'/',wait_until='networkidle')
 page.route('https://www.googletagmanager.com/**', lambda route: route.fulfill(content_type='application/javascript',body='window.__tagLoaded = true;'))
 page.get_by_role('button',name='Analytics preferences',exact=True).click()
 page.get_by_role('button',name='Allow analytics',exact=True).click()
 page.wait_for_function('window.__tagLoaded === true')
 assert page.locator('script[src*="gtag/js?id=G-JMK4H2LRD3"]').count()==1
 png=io.BytesIO(); Image.new('RGB',(8,8),'green').save(png,format='PNG')
 payload={'platform':'linkedin','uploader':'Test fixture','title':'Browser test','warnings':[], 'session':'test-session','assets':[{'id':'0','kind':'image','label':'Image 1','thumbnail':'/static/icons/icon-96.png'}]}
 page.route('**/api/info',lambda route: route.fulfill(content_type='application/json',body=json.dumps(payload)))
 page.route('**/api/download?*',lambda route: route.fulfill(content_type='image/png',headers={'Content-Disposition':'attachment; filename=test.png'},body=png.getvalue()))
 page.locator('#url').fill('https://www.linkedin.com/posts/test-activity-1234-abcd');page.locator('#ack').check();page.locator('#go').click()
 page.wait_for_selector('#assets .asset')
 with page.expect_download() as download:
  page.get_by_role('button',name='Download image',exact=True).click()
 assert download.value.failure() is None
 assert download.value.path().read_bytes()==png.getvalue()
 assert not errors,errors
 print('Desktop/mobile layout, navigation, consent rejection and invalid-URL flow passed. No JavaScript exceptions.')
 browser.close()
