
import logging
import time

import requests

from config import TMDB_API_KEY

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.themoviedb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

session = requests.Session()
session.headers.update({
    "User-Agent": "CinevoryxAI/1.0",
    "Accept": "application/json",
})


def get_image_url(path, size="w500"):
    """Convert a TMDB image path into a complete image URL."""
    if not path:
        return None

    return f"{TMDB_IMAGE_BASE_URL}/{size}{path}"


def tmdb_get(endpoint, params=None):
    """Make a TMDB request with limited retries."""
    request_params = {
        "api_key": TMDB_API_KEY,
        **(params or {}),
    }

    url = f"{TMDB_BASE_URL}/{endpoint.lstrip('/')}"

    for attempt in range(3):
        try:
            response = session.get(
                url,
                params=request_params,
                timeout=10,
            )

            # Retry temporary server failures and rate limits.
            if response.status_code in (429, 500, 502, 503, 504):
                if attempt < 2:
                    time.sleep(attempt + 1)
                    continue

            response.raise_for_status()
            return response.json()

        except (
            requests.exceptions.ConnectionError,
            requests.exceptions.Timeout,
        ):
            logger.warning(
                "TMDB connection problem, attempt %s/3",
                attempt + 1,
            )

            if attempt == 2:
                raise

            time.sleep(attempt + 1)


def search_movies(query: str):
    """Search TMDB for movies and return their metadata."""
    if not isinstance(query, str) or not query.strip():
        return []

    data = tmdb_get(
        "/search/movie",
        params={"query": query.strip()},
    )

    movies = []

    for movie in data.get("results", []):
        movies.append({
            "id": movie.get("id"),
            "title": movie.get("title"),
            "overview": movie.get("overview"),
            "release_date": movie.get("release_date"),
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
            "poster_path": movie.get("poster_path"),
            "poster_url": get_image_url(
                movie.get("poster_path")
            ),
            "backdrop_url": get_image_url(
                movie.get("backdrop_path"),
                "w780",
            ),
        })

    return movies


def get_movie_details(movie_id: int):
    """Get details about a movie using its TMDB ID."""
    movie = tmdb_get(f"/movie/{movie_id}")

    return {
        "id": movie.get("id"),
        "title": movie.get("title"),
        "overview": movie.get("overview"),
        "release_date": movie.get("release_date"),
        "rating": movie.get("vote_average"),
        "vote_count": movie.get("vote_count"),
        "runtime": movie.get("runtime"),
        "genres": [
            genre.get("name")
            for genre in movie.get("genres", [])
        ],
        "poster_path": movie.get("poster_path"),
        "poster_url": get_image_url(
            movie.get("poster_path")
        ),
        "backdrop_url": get_image_url(
            movie.get("backdrop_path"),
            "w780",
        ),
        "tagline": movie.get("tagline"),
        "status": movie.get("status"),
    }

# ==========================================
# ACTOR AND DIRECTOR INTELLIGENCE
# ==========================================

def search_people(name: str):
    """Search TMDB for actors, directors, and other film professionals."""
    if not isinstance(name, str) or not name.strip():
        return []

    data = tmdb_get(
        "/search/person",
        params={"query": name.strip()},
    )

    people = []

    for person in data.get("results", [])[:10]:
        people.append({
            "id": person.get("id"),
            "name": person.get("name"),
            "known_for_department": person.get(
                "known_for_department"
            ),
            "popularity": person.get("popularity"),
            "profile_url": get_image_url(
                person.get("profile_path"),
                "w185",
            ),
        })

    return people


def get_person_movie_credits(person_id: int):
    """Retrieve a person's acting and filmmaking credits."""
    if (
        isinstance(person_id, bool)
        or not isinstance(person_id, int)
        or person_id <= 0
    ):
        raise ValueError("Person ID must be a positive integer.")

    data = tmdb_get(
        f"/person/{person_id}/movie_credits"
    )

    credits = []

    # Acting roles
    for movie in data.get("cast", []):
        credits.append({
            "id": movie.get("id"),
            "title": movie.get("title"),
            "release_date": movie.get("release_date"),
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
            "character": movie.get("character"),
            "role": "Actor",
            "poster_url": get_image_url(
                movie.get("poster_path")
            ),
        })

    # Directing credits only
    for movie in data.get("crew", []):
        if movie.get("job") != "Director":
            continue

        credits.append({
            "id": movie.get("id"),
            "title": movie.get("title"),
            "release_date": movie.get("release_date"),
            "rating": movie.get("vote_average"),
            "vote_count": movie.get("vote_count"),
            "character": None,
            "role": "Director",
            "poster_url": get_image_url(
                movie.get("poster_path")
            ),
        })

    # Remove duplicates for the same movie and role
    unique_credits = {}

    for movie in credits:
        key = (movie["id"], movie["role"])
        unique_credits[key] = movie

    movies = list(unique_credits.values())

    # Sort by rating, then by number of votes
    movies.sort(
        key=lambda movie: (
            movie.get("rating") or 0,
            movie.get("vote_count") or 0,
        ),
        reverse=True,
    )

    return movies
