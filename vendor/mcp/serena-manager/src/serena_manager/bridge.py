from __future__ import annotations

import anyio
from anyio.streams.memory import MemoryObjectReceiveStream, MemoryObjectSendStream

from mcp.shared.message import SessionMessage


async def bridge_streams(
    upstream_read: MemoryObjectReceiveStream[SessionMessage | Exception],
    upstream_write: MemoryObjectSendStream[SessionMessage],
    downstream_read: MemoryObjectReceiveStream[SessionMessage | Exception],
    downstream_write: MemoryObjectSendStream[SessionMessage],
) -> None:
    async def forward(
        source: MemoryObjectReceiveStream[SessionMessage | Exception],
        sink: MemoryObjectSendStream[SessionMessage],
    ) -> None:
        try:
            async for item in source:
                if isinstance(item, Exception):
                    raise item
                await sink.send(item)
        except anyio.ClosedResourceError:
            raise
        finally:
            try:
                await sink.aclose()
            except Exception:
                pass

    async with anyio.create_task_group() as tg:
        tg.start_soon(forward, upstream_read, downstream_write)
        tg.start_soon(forward, downstream_read, upstream_write)
