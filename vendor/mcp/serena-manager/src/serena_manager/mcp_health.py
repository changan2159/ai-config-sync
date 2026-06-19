from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client


@asynccontextmanager
async def open_streamable_http_session(endpoint_url: str) -> AsyncIterator[ClientSession]:
    async with streamable_http_client(endpoint_url, terminate_on_close=False) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session

