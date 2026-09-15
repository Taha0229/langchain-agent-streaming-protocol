import logging
import os
from pathlib import Path

import uvicorn
from app.graph import build_study_graph
from app.server import CustomServer
from dotenv import find_dotenv, load_dotenv
from fastapi import FastAPI
from langgraph.checkpoint.memory import InMemorySaver
from app.transformers import QuizTransformer, FlashcardTransformer

logger = logging.getLogger(__name__)

load_dotenv(find_dotenv())

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
PORT = int(os.environ.get("PORT", "8000"))
RELOAD = os.environ.get("RELOAD", "1") != "0"
APP_DIR = Path(__file__).resolve().parent


def setup_logging() -> None:
    """Attach a handler to the root logger.

    Uvicorn configures only its own `uvicorn.*` loggers, so without this the
    root logger stays at WARNING with no handler and every `logger.info` in
    `app.*` is dropped. `create_app` calls it too, because `--reload` runs the
    server in a spawned child process where `main` never executes.
    """
    logging.basicConfig(
        level=LOG_LEVEL,
        format="%(levelname)s:  %(name)s - %(message)s",
        force=True,
    )


def create_app() -> FastAPI:
    """ASGI app factory.

    Uvicorn imports this by string ("app.main:create_app") rather than taking a
    prebuilt app object, so --reload can re-import it in a fresh worker process
    after every edit.
    """
    setup_logging()
    graph = build_study_graph(
        checkpointer=InMemorySaver(),
        transformers=[
            QuizTransformer,
            FlashcardTransformer,
        ],
    )
    return CustomServer(graph).build_app()


def main() -> None:
    setup_logging()
    logger.info(f"Agent Streaming Protocol server listening on http://localhost:{PORT}")
    uvicorn.run(
        "app.main:create_app",
        factory=True,
        host="0.0.0.0",
        port=PORT,
        reload=RELOAD,
        reload_dirs=[str(APP_DIR)],
        access_log=False,
    )


if __name__ == "__main__":
    main()
