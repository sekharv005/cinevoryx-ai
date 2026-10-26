# Cinevoryx AI

A movie search and chat application built with Python, FastAPI, Google Gemini, and the TMDB API.

I started this project to learn how to connect an LLM to external APIs using function calling. Instead of answering every question from the model alone, Cinevoryx can look up movie information from TMDB and use it in the conversation.

**Live site:** https://cinevoryx-ai.onrender.com/

## Screenshot

![Cinevoryx AI Homepage](https://github.com/user-attachments/assets/1d9d560e-eb66-4b35-825d-dad989dc96d8)

## Features

- Search movies by title and view posters, release dates, and ratings.
- Ask questions about movies, actors, and directors.
- Ask follow-up questions such as "Who directed this movie?" without repeating the title.
- Start a new chat when you want to clear the current conversation.

## Tech stack

- **Python + FastAPI** — backend and API routes
- **Google Gemini** — conversation and tool calling
- **TMDB API** — movie information
- **HTML, CSS, JavaScript** — frontend
- **Render** — deployment

## How it works

The frontend sends chat messages to the FastAPI backend. Gemini decides whether it needs information from TMDB and, when necessary, requests a tool call. The Python backend runs the corresponding function and returns the result to Gemini, which produces the final reply.

The backend also keeps a limited conversation history for each chat session, so questions like "Who is the director?" can refer to a movie mentioned earlier.

## Running locally

Clone the repository, open the project folder, and install the dependencies.

```bash
python -m venv .venv
```

Activate the environment on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Create a `.env` file in the project folder:

```env
GEMINI_API_KEY=your_key_here
TMDB_API_KEY=your_key_here
```

Start the server:

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000.

Don't commit your `.env` file or API keys.

## Notes

This is a learning project and I'm still improving it. Some questions take longer because the agent has to make multiple API calls, and AI-generated responses can occasionally be incorrect. I'm working on making the tool calls more reliable before adding more features.
