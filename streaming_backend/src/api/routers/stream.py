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
@router.get("/{video_id}", summary="Stream video by ID", tags=["stream"])
async def stream_video(
    video_id: int,
    db: Session = Depends(get_db),
    range_header: Optional[str] = Header(None, alias="Range"),
):
    """
    Stream video content with HTTP Range support.

    Parameters:
        video_id: ID of the video to stream
        Range header: Optional; passed through to upstream server

    Returns:
        StreamingResponse: proxied stream with appropriate headers
    """
    vid = get_video(db, video_id)
    if not vid:
        raise HTTPException(status_code=404, detail="Video not found")

    # For this minimal implementation, we always proxy the remote video_url.
    # In the future this could serve local files using similar Range logic.
    return await _proxy_range_stream(vid.video_url, range_header)
