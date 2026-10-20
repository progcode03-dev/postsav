# YouTube support — 20 October 2026

## Behavior

The home tool and `/youtube-downloader` accept individual watch, youtu.be, Shorts, embed and video live-link URLs. Links are normalized to one 11-character video ID, removing timestamps, tracking and playlist parameters. Channel pages, standalone playlist URLs, actual live/upcoming streams, private/member/age-restricted content and DRM are unsupported.

The result has one format/quality selector:

- MP4: the resolutions actually exposed to this server, including 144p, 240p, 360p, 480p, 720p, 1080p, 1440p and 2160p when available. Other exposed resolutions can also appear. Portrait quality is identified by the shorter edge. No upscaling occurs.
- MP3: 128, 192, 256 and 320 kbps conversions when an audio track and ffmpeg are available. A larger bitrate does not improve the source recording.
- Higher-resolution streams may need separate audio/video merging. MP4 can contain AV1/VP9, so playback compatibility depends on the device/player.
- The existing 250 MB limit is preserved. Options known to exceed it are omitted; unknown/approximate sizes are checked during transfer and after processing. The combined source streams must also fit the budget. Long 4K videos may therefore not have a selectable 4K output on this beta.

Only server-owned session choices are accepted by `/api/download`; client-provided yt-dlp selectors, file URLs and unsupported resolution IDs are rejected. YouTube ZIP downloads are rejected. Existing social-post bundles still work. Session tokens, rate/concurrency limits, cleanup and private no-store download responses are reused.

## Dependencies and deployment

Production Docker now includes Node 22 from its official Bookworm image, ffmpeg and `yt-dlp[default]` (including the matching EJS challenge-solver dependency). `youtube_sources.py` is included in the application image. No Instagram/browser cookies are imported for YouTube.

For local use, install ffmpeg on PATH and Node 22+ or Deno 2.3+. Without ffmpeg, only combined MP4 formats can be offered; MP3 and separate tracks are unavailable. Run the normal requirements installer to obtain the EJS dependency.

Render must deploy the new Docker image to get these dependencies; serving only updated static files is insufficient. If automatic deployment does not run, use Manual Deploy, Deploy latest commit. Account credentials, proxy services and methods to evade access restrictions have not been added.

## Validation

172 Python tests pass, including YouTube URL normalization, malicious/lookalike hosts, playlist rejection, actual format discovery, portrait labeling, missing ffmpeg, DRM/size filtering, private/live/wrong-video rejection, bot error messages, server-side selection validation, audio/video processing options, output names and download cleanup.

`tools/verify_youtube_processing.py` downloaded generated local fixture streams through real yt-dlp and used real ffmpeg to prepare one MP4 with video and audio plus four MP3 outputs. Every output was decoded and its expected stream types checked. Results: `youtube-processing-results.json`. These are processing tests, not proof of live YouTube availability.

`tools/check_youtube_ui.py` used fixture metadata to check 12 choices, MP4 2160p and MP3 320 kbps request selection, saved filenames, hidden ZIP controls, mobile overflow and JavaScript errors. Screenshots explicitly identify the fixture. SEO checks passed for all ten pages, including the new YouTube page.

A live YouTube metadata check from this machine was refused with “Sign in to confirm you’re not a bot.” The old yt-dlp test video was also unavailable. No successful live YouTube extraction/download was verified in this environment. YouTube may similarly restrict a Render/shared hosting address even with ffmpeg, EJS and Node installed. The application reports that restriction clearly rather than asking visitors for cookies or claiming the video has no formats.

The local Docker daemon was not running, so the image build itself could not be exercised here. Its dependency/module wiring was reviewed; deployment still needs production verification. Existing platform tests and Analytics consent checks remain passing.

## References

- [yt-dlp documentation](https://github.com/yt-dlp/yt-dlp)
- [YouTube JavaScript runtime and EJS setup](https://github.com/yt-dlp/yt-dlp/wiki/EJS)

Keep AdSense disabled until its separate approval and consent setup are complete. Adding YouTube support does not establish eligibility under Google's publisher policies.

## Hosted follow-up

The Render deployment of `32bb265` became live: `/youtube-downloader` returned 200, and readiness reported ffmpeg, Node and EJS present. All ten pages passed the deployed SEO checks. A hosted lookup of the public Big Buck Bunny sample returned 502 with the message that YouTube could not expose the video. Consequently successful live YouTube extraction/download is still unverified; the processing and browser tests above must not be represented as proof that every public YouTube URL works on Render.

## Investigation of every-link failures

On 20 October, bounded provider warnings identified the actual hosted failure: YouTube returned HTTP 429 for its webpage and HTTP 403 for the player API attempts. The final yt-dlp exception omitted those warnings and only said “Failed to extract any player response.” This caused the application to incorrectly suggest that each video was unavailable. Production already had yt-dlp 2026.08.19, Node and EJS; updating page markup or the quality selector cannot resolve this network refusal.

The same public video was successfully looked up on the development machine without browser cookies. Its actual 144p MP4 (4,269,067 bytes) and 128 kbps MP3 (3,143,852 bytes) were downloaded using the application's processing functions, decoded successfully with ffmpeg and removed after testing. This verifies the local pipeline, not the Render connection.

The application now examines warnings as well as the final exception, reports upstream blocking with HTTP 503 and `youtube_server_blocked`, and preserves distinct handling for unavailable videos. Download-stage blocks use the same handling and release job slots. Bounded sanitized provider diagnostics stay in operator logs rather than the public API. The site does not automatically retry blocked downloads.

All 178 Python tests pass, including regressions for hidden HTTP warnings, unavailable-video classification, private diagnostics, download-slot cleanup and proxy configuration validation.

### Restoring the hosted connection

The current Render connection remains blocked. There is no working alternative server or proxy configured. The feature must not be described as working publicly until an actual deployed lookup and media download succeed.

An operator can either run this application on a server whose outbound connection YouTube accepts, or configure a trusted HTTP(S) proxy they are authorized to use. Test that connection before purchasing or migrating; a different hosting provider alone does not guarantee access.

For an authorized proxy, set `YOUTUBE_PROXY_URL` in Render's secret environment settings to the provider's HTTP(S) proxy URL (for example, `http://USER:PASSWORD@HOST:PORT`), then redeploy. Percent-encode special characters in credentials. Never commit the real value, put it in browser JavaScript, or send it through `/api/info`. The same setting is used for metadata and media downloads because extracted media can be bound to the originating connection. No proxy is supplied or selected automatically, and setting this variable does not guarantee YouTube will accept the connection.

After deployment, fetch a known public video through `/youtube-downloader` and download both a small MP4 and an MP3. Verify audio/video playback. `/readyz` only checks dependencies; it does not establish upstream YouTube availability. If `youtube_server_blocked` persists, inspect Render's sanitized logs and resolve access with the hosting/network provider.

The upstream [yt-dlp FAQ on HTTP 429](https://github.com/yt-dlp/yt-dlp/wiki/FAQ#http-error-429-too-many-requests-or-402-payment-required) explains that this response indicates an IP access block.
