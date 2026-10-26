"""Cinevoryx AI FastAPI application."""

import logging
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from uuid import UUID, uuid4

import requests
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import run_agent
from tmdb_service import search_movies, get_movie_details

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"

app = FastAPI(
    title="Cinevoryx AI API",
    description="Conversational AI movie research and discovery agent",
    version="1.3.0",
)
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

# In-memory, per-process session history. Resets on restart or redeployment.
# Run a single worker until a shared session store is added.
conversations = OrderedDict()
memory_lock = Lock()
MAX_SESSIONS = 100
MAX_MESSAGES = 12


class AskRequest(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    session_id: str | None = None


class NewChatRequest(BaseModel):
    session_id: str


def normalize_session_id(session_id: str | None) -> str:
    if session_id is None:
        return str(uuid4())
    try:
        return str(UUID(session_id))
    except (ValueError, AttributeError, TypeError) as error:
        raise HTTPException(status_code=400, detail="Invalid session ID") from error


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    """Liveness endpoint; does not check external Gemini/TMDB availability."""
    return {"status": "ok", "service": "cinevoryx-ai"}


@app.post("/ask")
def ask(request: AskRequest):
    session_id = normalize_session_id(request.session_id)
    with memory_lock:
        history = list(conversations.get(session_id, []))

    try:
        answer = run_agent(request.query, history=history)
    except (ValueError, TypeError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        logger.exception("Unexpected error while running Cinevoryx agent")
        raise HTTPException(
            status_code=503,
            detail="AI service is temporarily unavailable.",
        ) from error

    with memory_lock:
        updated_history = conversations.get(session_id, []).copy()
        updated_history.extend([
            {"role": "user", "content": request.query},
            {"role": "model", "content": answer},
        ])
        conversations[session_id] = updated_history[-MAX_MESSAGES:]
        conversations.move_to_end(session_id)
        while len(conversations) > MAX_SESSIONS:
            conversations.popitem(last=False)

    return {"answer": answer, "session_id": session_id}


@app.post("/new-chat")
def new_chat(request: NewChatRequest):
    session_id = normalize_session_id(request.session_id)
    with memory_lock:
        conversations.pop(session_id, None)
    return {"message": "Conversation cleared", "session_id": str(uuid4())}


@app.get("/api/movies/search")
def movie_search(query: str = Query(min_length=1, max_length=200)):
    try:
        movies = search_movies(query.strip())
        return {"query": query, "count": len(movies), "movies": movies[:12]}
    except requests.exceptions.RequestException as error:
        logger.warning("TMDB movie search failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=503, detail="Movie service is temporarily unavailable."
        ) from error


@app.get("/api/movies/{movie_id}")
def movie_details(movie_id: int):
    if movie_id <= 0:
        raise HTTPException(status_code=400, detail="Movie ID must be positive.")
    try:
        return {"movie": get_movie_details(movie_id)}
    except requests.exceptions.HTTPError as error:
        if error.response is not None and error.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Movie not found.") from error
        logger.warning("TMDB movie details HTTP error: %s", type(error).__name__)
        raise HTTPException(
            status_code=503, detail="Movie service is temporarily unavailable."
        ) from error
    except requests.exceptions.RequestException as error:
        logger.warning("TMDB movie details request failed: %s", type(error).__name__)
        raise HTTPException(
            status_code=503, detail="Movie service is temporarily unavailable."
        ) from error
