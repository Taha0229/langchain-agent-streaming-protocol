import asyncio
import contextlib
import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from app.sessions import LocalProtocolGraph, LocalThreadSession
from app.threads import (get_thread_history, get_thread_state,
                         update_thread_state)
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger(__name__)


class CustomServer:
    def __init__(self, graph: LocalProtocolGraph):
        self._graph = graph
        self._sessions: dict[str, LocalThreadSession] = {}
        pass

    def _session(self, thread_id: str) -> LocalThreadSession:
        session = self._sessions.get(thread_id)
        if not session: 
            session = LocalThreadSession(
                graph=self._graph,
                thread_id=thread_id,
            )
            self._sessions[thread_id] = session
        return session

    def build_app(self) -> FastAPI:
        app = FastAPI(
            title="LangGraph BE streaming test server",
            description="LangGraph BE streaming test server",
            version="1.0.0",
        )

        # CORS Middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["*"],
        )

        @app.get("/threads/{thread_id}/state")
        async def _get_state(thread_id: str) -> Response:
            logger.info(f"hitting `_get_state`")
            # thread_id = request.path_params["thread_id"]

            try:
                state = await get_thread_state(graph=self._graph, thread_id=thread_id)
            except KeyError:
                return JSONResponse(
                    {
                        "error": "not_found",
                        "message": f"Thread {thread_id} not found",
                    },
                    status_code=404,
                )
            return JSONResponse(state)

        @app.post(
            "/threads/{thread_id}/state"
        )  # This is being used to create thread as well as to patch it
        async def _post_state(request: Request) -> Response:
            logger.info(f"hitting `_post_state`")
            thread_id = request.path_params["thread_id"]

            body = await request.json()
            values = body.get("values") if isinstance(body, dict) else None
            checkpoint = body.get("checkpoint") if isinstance(body, dict) else None
            as_node = body.get("as_node") if isinstance(body, dict) else None
            try:
                state = await update_thread_state(
                    self._graph,
                    thread_id,
                    values=values if isinstance(values, dict) else None,
                    checkpoint=checkpoint if isinstance(checkpoint, dict) else None,
                    as_node=as_node if isinstance(as_node, str) else None,
                )
            except Exception as exc:  # noqa: BLE001
                return JSONResponse(
                    {
                        "error": "invalid_state_update",
                        "message": str(exc),
                    },
                    status_code=422,
                )
            return JSONResponse(state)

        @app.post("/threads")
        async def _post_state_protocol(request: Request) -> Response:
            logger.info(f"hitting `_post_state`")

            body = await request.json()
            logger.info(f"body: \n{body}")
            thread_id = body["thread_id"]
            if_exists = body["if_exists"]
            metadata = body["metadata"]

            # TODO persist metadata with the thread
            # ~ looks like metadata is updated only by patch

            try:
                state = await get_thread_state(graph=self._graph, thread_id=thread_id)
            except KeyError:
                if if_exists == "raise":
                    raise FileExistsError(
                        f"Raised due to handler - {if_exists} | thread id already exists"
                    )
                elif if_exists == "do_nothing":
                    logger.info(
                        f"Thread id already exists: {thread_id}. Returning as it is with last state"
                    )
                    state = await update_thread_state(
                        graph=self._graph, thread_id=thread_id
                    )
                else:
                    raise ValueError(
                        f"Invalid if exists handler passed: {if_exists}. Options are `do_nothing`, `raise`"
                    )
            except Exception as e:
                raise e

            values: dict = state.get("values", {})

            messages = values.get("messages")
            if messages:
                messages = values.pop("messages")

            response = {
                "thread_id": thread_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "metadata": metadata,
                "status": "idle",
                "values": values,
                **({"messages": messages} if messages else {}),
            }

            return JSONResponse(response)

        @app.post("/threads/{thread_id}/history")
        async def _post_history(request: Request) -> Response:
            thread_id = request.path_params["thread_id"]
            body = await request.json()
            parsed = body if isinstance(body, dict) else {}
            limit_raw = parsed.get("limit", 10)
            limit = int(limit_raw) if isinstance(limit_raw, int) else 10
            before = parsed.get("before")

            try:
                history = await get_thread_history(
                    self._graph,
                    thread_id,
                    limit=limit,
                    before=before,
                )
            except KeyError:
                return JSONResponse(
                    {
                        "error": "not_found",
                        "message": f"Thread {thread_id} not found",
                    },
                    status_code=404,
                )
            return JSONResponse(history)

        @app.post("/threads/{thread_id}/commands")
        async def _commands(request: Request) -> JSONResponse:
            thread_id = request.path_params["thread_id"]
            command = await request.json()
            result = await self._session(thread_id).handle_command(command)
            return JSONResponse(result)
        
    

        @app.post("/threads/{thread_id}/stream/events")
        @app.post("/threads/{thread_id}/stream")
        async def _stream(request: Request) -> StreamingResponse:
            thread_id = request.path_params["thread_id"]
            params: dict[str, Any] = await request.json()
            return StreamingResponse(
                self._session(thread_id).stream(params),
                media_type="text/event-stream",
                headers={"cache-control": "no-cache"},
            )

        return app
