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
