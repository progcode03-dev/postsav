# PostSav redesign and SEO review — 14 October 2026

## Delivered

- Replaced the floating gradient cards and stock photography with an editorial layout: paper background, ink text, forest-green accent, serif headings and a practical file-format panel. The full site uses the new responsive design, including policy pages, results and mobile navigation.
- Created an original folded-page P monogram as SVG, ICO and PNG icons; a matching social card; and compressed native file illustrations. Brand assets use content-versioned URLs to refresh cached favicons and social previews.
- Preserved the useful existing per-page titles, descriptions, canonicals, platform content, sitemap and structured data. Added social-image accessibility metadata and a LinkedIn sign-in/share-link FAQ based on the actual observed failure.
- Expanded the full machine-readable summary to include the real configured policy pages. Updated content modification dates without changing historical media-test dates or inventing fresh success claims.
- Added CSP, clickjacking protection and browser feature restrictions. CSP hashes structured data rather than permitting arbitrary inline JavaScript; inline styles remain allowed for existing image positioning. Advertising stays off; its explicitly enabled CSP is broader to accommodate Google's advertising partners and needs verification before activation.
- Rejected malformed canonical configuration containing credentials, paths, query strings or fragments. Filtered preview URLs to platform CDN hosts. Download busy states now leave Analytics privacy choices accessible.
- Replaced the outdated SEO strategy document with actionable account setup and maintenance instructions backed by current Google guidance.

## Validation

156 Python tests pass, including security-policy/304 consistency, canonical-setting rejection, preview-host filtering and policy-summary coverage. Analytics consent logic checks pass.

Browser checks at 1440-pixel desktop and 375-pixel mobile widths passed: no horizontal page overflow across the selected pages, working mobile menu, rejected Analytics with no tag loaded, accepted Analytics loading exactly one intercepted tag, a useful invalid-URL error, and a successful saved image from a mocked API response. The mock validates the browser download interaction; it does not validate a platform's current availability.

Local Lighthouse mobile emulation scored 100 performance / 100 accessibility / 100 best practices / 100 SEO. LCP was 1.3 seconds, CLS 0 and total blocking time 0 ms. These are local measurements, not production speed guarantees or rankings. Full report: `lighthouse-redesign.json`.

The four feature images decreased from 111,148 to 12,800 bytes (about 89%). The social card decreased from 85,088 to 43,329 bytes (about 49%). The site has no external font request or UI framework bundle.

## Account work

Follow `SEO.md` for Search Console/Bing verification, sitemap submission, Analytics checks, AdSense preparation and hosting considerations. Keep your Analytics and AdSense identifiers already configured; the Search Console token is a separate setting. Google says special AI markup/files are not required for its AI search features. Original content, supported claims, crawlability and reliable availability matter.

## Limits

This is not a penetration test or a guarantee that every platform post will work. The deployment remains a single-worker beta: rate limiting and download slots are process-local, and extraction depends on public platform responses. Broad search rankings, Google indexing, AdSense approval and AI citations cannot be guaranteed by adding metadata.
