"""Transcript fetch via youtube-transcript-api 1.x (spec §6 step 2).

Free, no auth — but YouTube IP-blocks bursts, so we throttle and back off.
Only PERMANENT misses (captions disabled / none in English / video gone) are
negative-cached; IP blocks are never cached, so a re-run resumes cleanly.
"""

import time

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    IpBlocked,
    NoTranscriptFound,
    RequestBlocked,
    TranscriptsDisabled,
    VideoUnavailable,
)

from . import cache

_THROTTLE_S = 4          # pause between live fetches (cache hits skip it)
_BLOCK_RETRIES = 1       # one 60s backoff, then trip the circuit — keeps /connect snappy
_BLOCK_BACKOFF_S = 60

_last_fetch = 0.0
_circuit_open = False  # once the IP block outlasts all retries, stop hammering


def reset_circuit() -> None:
    """Called at the start of each corpus build so a lifted IP block is retried."""
    global _circuit_open
    _circuit_open = False


def get_transcript(video_id: str) -> str | None:
    global _last_fetch, _circuit_open
    if (hit := cache.get("transcripts", video_id)) is not None:
        return hit["text"]
    if _circuit_open:
        return None  # not cached — a later re-run resumes here
    for attempt in range(_BLOCK_RETRIES + 1):
        wait = _THROTTLE_S - (time.monotonic() - _last_fetch)
        if wait > 0:
            time.sleep(wait)
        _last_fetch = time.monotonic()
        try:
            fetched = YouTubeTranscriptApi().fetch(
                video_id, languages=["en", "en-US", "en-GB"]
            )
            text = " ".join(s.text for s in fetched.snippets).strip() or None
            cache.put("transcripts", video_id, {"text": text})
            return text
        except (TranscriptsDisabled, NoTranscriptFound, VideoUnavailable):
            cache.put("transcripts", video_id, {"text": None})  # permanent miss
            return None
        except (IpBlocked, RequestBlocked):
            if attempt == _BLOCK_RETRIES:
                _circuit_open = True
                print(f"WARN: IP block outlasted retries at {video_id}; "
                      "skipping remaining fetches this run (re-run to resume)")
                return None
            backoff = _BLOCK_BACKOFF_S * (2**attempt)
            print(f"WARN: YouTube IP block; sleeping {backoff}s (attempt {attempt + 1})")
            time.sleep(backoff)
        except Exception as e:  # unknown transient — skip, don't poison the cache
            print(f"WARN: transcript fetch failed for {video_id}: {type(e).__name__}")
            return None
    return None
