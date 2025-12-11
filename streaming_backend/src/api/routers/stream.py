from typing import Optional

import aiohttp
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.api.services.video_service import get_video
from src.db.session import get_db

router = APIRouter()


async def _proxy_range_stream(url: str, range_header: Optional[str]) -> StreamingResponse:
    """
    Stream bytes from a remote URL with Range support by proxying headers.

    This helper:
      - Forwards the incoming `Range` header (if present) to the upstream server.
      - Mirrors key headers from the upstream response:
        `Content-Type`, `Content-Length`, `Accept-Ranges`, and `Content-Range`.
      - Preserves the upstream HTTP status code (200 or 206).
      - Ensures the aiohttp ClientSession is closed once streaming completes.
    """
    headers = {}
    if range_header:
        headers["Range"] = range_header

    session_timeout = aiohttp.ClientTimeout(total=None, connect=30)
    client = aiohttp.ClientSession(timeout=session_timeout)
    try:
        upstream = await client.get(url, headers=headers)
        if upstream.status in (200, 206):
            # Prepare headers for the client
            resp_headers = {}
            for key in ["Content-Type", "Content-Length", "Accept-Ranges", "Content-Range"]:
                if key in upstream.headers:
                    resp_headers[key] = upstream.headers[key]

            async def iterator():
                async for chunk in upstream.content.iter_chunked(1024 * 64):
                    yield chunk
                await upstream.release()

            status_code = upstream.status
            return StreamingResponse(iterator(), status_code=status_code, headers=resp_headers)
        else:
            body = await upstream.text()
            raise HTTPException(status_code=upstream.status, detail=f"Upstream error: {body}")
    finally:
        # ClientSession must be closed; StreamingResponse will have consumed upstream already
        await client.close()


# PUBLIC_INTERFACE
@router.get(
    "/{video_id}",
    summary="Stream video by ID",
    description=(
        "Proxy video bytes from the video's `video_url` field with HTTP Range support. "
        "Clients should send a `Range` header for seeking. The endpoint forwards this "
        "header upstream and exposes `Accept-Ranges`, `Content-Range`, `Content-Type`, "
        "and `Content-Length` where available."
    ),
    tags=["stream"],
)
async def stream_video(
    video_id: int,
    db: Session = Depends(get_db),
    range_header: Optional[str] = Header(
        default=None,
        alias="Range",
        description="Standard HTTP Range header, e.g. 'bytes=0-'.",
    ),
):
    """
    Stream video content with HTTP Range support.

    Parameters:
        video_id: ID of the video to stream.
        range_header: Optional; passed through to the upstream server as `Range`.

    Returns:
        StreamingResponse: Proxied stream with appropriate content and range headers.

    Raises:
        HTTPException(404): If the video does not exist.
        HTTPException(4xx/5xx): If the upstream video URL responds with an error.
    """
    vid = get_video(db, video_id)
    if not vid:
        raise HTTPException(status_code=404, detail="Video not found")

    # For this minimal implementation, we always proxy the remote video_url.
    # In the future this could serve local files using similar Range logic.
    return await _proxy_range_stream(vid.video_url, range_header)
