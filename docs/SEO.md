# SEO and GEO runbook — updated 14 October 2026

## What is implemented

- Server-rendered home, LinkedIn, Pinterest, Instagram, About and policy pages. Each has a distinct title, description, H1, canonical and social preview.
- Crawlable internal links, breadcrumbs, platform-specific explanations and FAQs generated from the same content as the structured data.
- Robots.txt, XML sitemap with actual content update dates, useful 404 responses, canonical host/scheme redirects and ETag revalidation.
- Original folded-page logo, favicon sizes, a 1200 x 630 social card and compressed file-format illustrations. System fonts avoid external font requests.
- Optional consent-based Analytics, separate AdSense verification and ads.txt. Ads remain disabled.
- Browser security headers: CSP, frame protection, nosniff, feature restrictions and appropriate referrer policies. Media requests validate supported hosts and redirect hops; files and requests have limits.
- llms.txt and llms-full.txt are descriptive summaries, including configured policy text. They are not Google ranking signals or prerequisites for AI search.

## Your account checklist

1. **Google Search Console:** add `https://social-downloader-75g8.onrender.com/` as a URL-prefix property. Choose HTML-tag verification, copy its token into `GOOGLE_SITE_VERIFICATION` in Render, deploy, then click Verify. Submit `sitemap.xml`. Inspect the home page and each of the three platform pages and request indexing once if needed. Watch Page indexing and Performance reports rather than repeatedly resubmitting.
2. **Bing Webmaster Tools:** import the verified property from Search Console or use its HTML meta token via `BING_SITE_VERIFICATION`. Submit the sitemap. IndexNow is available via `python indexnow.py https://social-downloader-75g8.onrender.com` after substantive updates.
3. **Analytics:** ID `G-JMK4H2LRD3` is configured. Check Realtime after visiting and accepting Analytics. Disable Enhanced measurement in the web stream to avoid automatic form/link events exposing submitted post URLs. Link Search Console to Analytics if useful. Analytics itself does not boost rankings.
4. **AdSense:** verification for `ca-pub-7254853329853324` and ads.txt are configured. Leave `ADSENSE_ENABLED=0` until approval and Google's advertising consent messages are ready. This downloader's eligibility needs review against Google's policy on streaming-video downloads prohibited by the provider. See GOOGLE-SETUP.md.
5. **Hosting:** confirm the service reliably returns crawlable pages rather than host-generated sleep/error pages. Reliable availability matters more than an uptime trick. A custom domain is optional; if you add one, set `SITE_URL` to its HTTPS origin, retain redirects from the old host and register the new property in Search Console/Bing. Do not change URLs casually.
6. **Content:** keep the contact information accurate. Publish substantive improvements when you have something useful to add, and rerun real-media validation before changing `TESTED_ON` or historical success counts. Avoid duplicate keyword landing pages, fabricated reviews, bought links and invented test results.

## What to monitor

Search Console impressions, clicks, query relevance and indexing errors; Analytics consented visits and engagement; and actual download success by platform. Broad terms are competitive. Specific queries such as LinkedIn carousel slides and Pinterest pin.it images match the useful distinctions on these pages. No ranking or citation is guaranteed.

## Maintenance

Run `python -m unittest discover -q`, `node tools/test_privacy.cjs`, `python verify_seo.py <origin>` and `python tools/check_deployed.py <origin>`. The latter uses a small sample of historical public posts; upstream access can change. Rebuild brand assets with `python tools/build_brand.py` (Pillow). The scripts under tools/make_icons.py and tools/make_og_image.py call the same builder.

Google's current AI-search guidance uses normal SEO fundamentals: accessible, useful, accurate content and clear supporting context. It explicitly says special AI files/markup are unnecessary. FAQ and HowTo schema describe the visible content, but do not promise a rich result.

Official references:

- [Google AI optimization guidance](https://developers.google.com/search/docs/fundamentals/ai-optimization-guide)
- [Canonical URL guidance](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
- [Sitemap guidance](https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap)
- [Search Console setup](https://support.google.com/webmasters/answer/9008080)
- [Flask security guidance](https://flask.palletsprojects.com/en/stable/web-security/)
