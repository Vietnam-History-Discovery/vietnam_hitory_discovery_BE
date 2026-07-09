"""Generic SSE formatting — no knowledge of chat/timeline/any specific mode.

Wraps any generator of {"event": str, "data": dict} into a StreamingResponse.
Reusable by any future streaming endpoint, not just /query/stream.
"""
import json

from fastapi.responses import StreamingResponse


def _format_event(event: dict) -> str:
    return f"event: {event['event']}\ndata: {json.dumps(event['data'], ensure_ascii=False)}\n\n"


def sse_response(event_generator) -> StreamingResponse:
    def gen():
        try:
            for event in event_generator:
                yield _format_event(event)
        except Exception as exc:
            yield _format_event({"event": "error", "data": {"message": str(exc)}})

    return StreamingResponse(gen(), media_type="text/event-stream")
