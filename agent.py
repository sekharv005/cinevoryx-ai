
import logging

from google import genai
from google.genai import types

from config import GEMINI_API_KEY
from tmdb_service import (
    search_movies,
    get_movie_details,
    search_people,
    get_person_movie_credits,
)


# --------------------------------------------------
# 1. Logging and Gemini client
# --------------------------------------------------

logger = logging.getLogger(__name__)

client = genai.Client(api_key=GEMINI_API_KEY)


# --------------------------------------------------
# 2. Tools available to the Gemini agent
# --------------------------------------------------

movie_tools = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_movies",
            description=(
                "Searches the TMDB movie database and returns "
                "movies matching a movie title or search term. "
                "Use this tool to identify specific movies."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Movie title or search term.",
                    }
                },
                "required": ["query"],
            },
        ),
        types.FunctionDeclaration(
            name="get_movie_details",
            description=(
                "Gets detailed information about a movie "
                "using its TMDB movie ID."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "movie_id": {
                        "type": "integer",
                        "description": "The TMDB movie ID.",
                    }
                },
                "required": ["movie_id"],
            },
        ),
        types.FunctionDeclaration(
            name="search_people",
            description=(
                "Search TMDB for actors, directors, and filmmakers by name. "
                "Use the returned person ID for movie credits."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Actor or director name.",
                    }
                },
                "required": ["name"],
            },
        ),
        types.FunctionDeclaration(
            name="get_person_movie_credits",
            description=(
                "Retrieve an actor's or director's TMDB movie credits "
                "using their TMDB person ID. Includes ratings and vote counts."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "person_id": {
                        "type": "integer",
                        "description": "The TMDB person ID, not a movie ID.",
                    }
                },
                "required": ["person_id"],
            },
        ),
    ]
)


# --------------------------------------------------
# 3. Validate user input
# --------------------------------------------------

def validate_user_input(user_query: str) -> str:
    """Validate user input before sending it to Gemini."""

    if not isinstance(user_query, str):
        raise TypeError("The question must be text.")

    user_query = user_query.strip()

    if not user_query:
        raise ValueError(
            "Please enter a movie-related question."
        )

    if len(user_query) > 2000:
        raise ValueError(
            "Your question is too long. "
            "Maximum length is 2000 characters."
        )

    return user_query


# --------------------------------------------------
# 4. Validate and execute movie tools
# --------------------------------------------------

def execute_movie_tool(tool_name: str, tool_args: dict):
    """Validate tool arguments before calling TMDB."""

    if not isinstance(tool_args, dict):
        return {
            "error": "Tool arguments must be an object."
        }

    if tool_name == "search_movies":

        if set(tool_args.keys()) != {"query"}:
            return {
                "error": "Invalid arguments for search_movies."
            }

        query = tool_args.get("query")

        if not isinstance(query, str):
            return {
                "error": "Search query must be text."
            }

        query = query.strip()

        if not query:
            return {
                "error": "Search query cannot be empty."
            }

        if len(query) > 200:
            return {
                "error": "Search query is too long."
            }

        return search_movies(query)

    elif tool_name == "get_movie_details":

        if set(tool_args.keys()) != {"movie_id"}:
            return {
                "error": "Invalid arguments for get_movie_details."
            }

        movie_id = tool_args.get("movie_id")

        if (
            isinstance(movie_id, bool)
            or not isinstance(movie_id, int)
            or movie_id <= 0
        ):
            return {
                "error": "Movie ID must be a positive integer."
            }

        return get_movie_details(movie_id)

    elif tool_name == "search_people":
        if set(tool_args.keys()) != {"name"}:
            return {"error": "Invalid arguments for search_people."}

        name = tool_args.get("name")
        if not isinstance(name, str) or not name.strip():
            return {"error": "Person name must be non-empty text."}
        if len(name.strip()) > 200:
            return {"error": "Person name is too long."}

        return search_people(name.strip())

    elif tool_name == "get_person_movie_credits":
        if set(tool_args.keys()) != {"person_id"}:
            return {"error": "Invalid arguments for get_person_movie_credits."}

        person_id = tool_args.get("person_id")
        if (
            isinstance(person_id, bool)
            or not isinstance(person_id, int)
            or person_id <= 0
        ):
            return {"error": "Person ID must be a positive integer."}

        return get_person_movie_credits(person_id)

    return {
        "error": f"Unsupported tool: {tool_name}"
    }


# --------------------------------------------------
# 5. Build conversation context
# --------------------------------------------------

def build_conversation(
    user_query: str,
    history: list[dict] | None = None,
):
    """
    Build Gemini conversation contents using
    previous user and assistant messages.
    """

    contents = []

    # Keep the most recent 12 messages
    recent_history = (history or [])[-12:]

    for message in recent_history:

        if not isinstance(message, dict):
            continue

        role = message.get("role")
        text = message.get("content")

        if role not in ("user", "model"):
            continue

        if not isinstance(text, str):
            continue

        text = text.strip()

        if not text:
            continue

        contents.append(
            types.Content(
                role=role,
                parts=[
                    types.Part.from_text(text=text)
                ],
            )
        )

    # Add the current question after the history
    contents.append(
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=user_query)
            ],
        )
    )

    return contents


# --------------------------------------------------
# 6. Main Cinevoryx AI agent
# --------------------------------------------------

def run_agent(
    user_query: str,
    tool_log: list[dict] | None = None,
    history: list[dict] | None = None,
):
    """
    Run the Cinevoryx AI movie research agent.

    Supports:
    - Gemini reasoning
    - TMDB tool calling
    - Multi-turn conversation memory
    - Input validation
    - Tool execution logging
    """

    # Validate incoming user question
    user_query = validate_user_input(user_query)

    # Build conversation with previous messages
    contents = build_conversation(
        user_query=user_query,
        history=history,
    )

    max_iterations = 5

    for iteration in range(max_iterations):

        print(f"\n--- Agent Step {iteration + 1} ---")

        # Call Gemini once per iteration
        try:
            response = client.models.generate_content(
                model="gemini-3.5-flash-lite",
                contents=contents,
                config=types.GenerateContentConfig(
                    tools=[movie_tools],
                    system_instruction=(
                        "You are Cinevoryx AI, an intelligent "
                        "movie research and discovery assistant. "
                        "Use conversation history to understand "
                        "follow-up questions and references such "
                        "as 'he', 'she', 'his', 'her', 'it', "
                        "and 'that movie'. "
                        "When users ask about movies, actors, "
                        "directors, or recommendations, answer "
                        "clearly and helpfully. "
                        "Use TMDB tools when relevant to retrieve "
                        "movie information. For questions about an "
                        "actor or director, search_people first, "
                        "then get_person_movie_credits with their "
                        "person ID. For follow-up questions, use "
                        "the person identified in conversation. "
                        "Distinguish acting from directing credits. "
                        "Ratings are TMDB user ratings, not "
                        "objective quality scores. "
                        "Do not invent ratings, runtimes, "
                        "release dates, or other movie facts. "
                        "If a tool cannot provide the requested "
                        "information, explain the limitation. "
                        "Do not claim to have verified current "
                        "information unless it was retrieved."
                    ),
                ),
            )

        except Exception:
            logger.exception("Gemini request failed")

            return (
                "Sorry, Cinevoryx AI is temporarily unavailable. "
                "Please try again."
            )

        # Validate Gemini response
        if not response.candidates:
            logger.error("Gemini returned no candidates")

            return (
                "Sorry, Cinevoryx AI couldn't generate an answer. "
                "Please try again."
            )

        candidate = response.candidates[0]

        if not candidate.content or not candidate.content.parts:
            logger.warning(
                "Gemini returned empty candidate content"
            )

            return (
                "Sorry, Cinevoryx AI couldn't generate "
                "a complete response."
            )

        parts = candidate.content.parts

        # Add Gemini response to the current conversation
        contents.append(candidate.content)

        function_call_found = False
        tool_response_parts = []

        # Process requested tool calls
        for part in parts:

            if not part.function_call:
                continue

            function_call_found = True

            function_call = part.function_call

            tool_name = function_call.name
            tool_args = dict(function_call.args or {})

            print("Agent decided:")
            print("Tool:", tool_name)
            print("Arguments:", tool_args)

            # Execute tool safely
            try:
                tool_result = execute_movie_tool(
                    tool_name,
                    tool_args,
                )

                if (
                    isinstance(tool_result, dict)
                    and "error" in tool_result
                ):
                    print(
                        "Tool rejected or failed:",
                        tool_result["error"],
                    )
                else:
                    print("Tool executed successfully.")

            except Exception:
                logger.exception(
                    "Movie tool execution failed"
                )

                tool_result = {
                    "error": (
                        "The movie service is "
                        "temporarily unavailable."
                    )
                }

                print("Tool execution failed.")

            # Record tool calls for evaluation
            if tool_log is not None:
                tool_log.append({
                    "tool": tool_name,
                    "args": tool_args,
                    "success": not (
                        isinstance(tool_result, dict)
                        and "error" in tool_result
                    ),
                })

            # Prepare tool response for Gemini
            tool_response_parts.append(
                types.Part.from_function_response(
                    name=tool_name,
                    response={
                        "result": tool_result
                    },
                )
            )

        # Return final answer if Gemini did not call tools
        if not function_call_found:

            final_answer = (
                response.text
                or "Sorry, I couldn't generate a complete answer."
            )

            print("\nFinal Answer:")
            print(final_answer)

            return final_answer

        # Return all tool results to Gemini
        contents.append(
            types.Content(
                role="user",
                parts=tool_response_parts,
            )
        )

    # Stop the agent after reaching the step limit
    logger.warning(
        "Agent reached the maximum iteration limit"
    )

    return (
        "Cinevoryx AI couldn't complete your request "
        "within its step limit. "
        "Please try a simpler question."
    )


# --------------------------------------------------
# 7. Run Cinevoryx AI directly
# --------------------------------------------------

if __name__ == "__main__":

    run_agent(
        "Find The Dark Knight and give me "
        "its rating and runtime."
    )
