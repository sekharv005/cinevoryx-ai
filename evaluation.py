
from typing import TypedDict


class EvaluationResult(TypedDict):
    passed: bool
    score: float
    reason: str


def evaluate_answer(
    answer: str,
    required_keywords: list[str] | None = None,
) -> EvaluationResult:
    """Check whether an answer contains expected information."""

    if not answer or not answer.strip():
        return {
            "passed": False,
            "score": 0.0,
            "reason": "The answer is empty.",
        }

    required_keywords = required_keywords or []

    missing = [
        keyword
        for keyword in required_keywords
        if keyword.casefold() not in answer.casefold()
    ]

    if missing:
        score = (
            len(required_keywords) - len(missing)
        ) / len(required_keywords)

        return {
            "passed": False,
            "score": score,
            "reason": f"Missing expected information: {missing}",
        }

    return {
        "passed": True,
        "score": 1.0,
        "reason": "Basic answer checks passed.",
    }


def evaluate_tool_call(
    actual_tool: str,
    expected_tool: str,
    actual_args: dict,
    expected_args: dict,
) -> EvaluationResult:
    """Evaluate the selected tool and its arguments."""

    tool_correct = actual_tool == expected_tool
    args_correct = actual_args == expected_args

    score = (
        int(tool_correct) + int(args_correct)
    ) / 2

    return {
        "passed": tool_correct and args_correct,
        "score": score,
        "reason": (
            f"Tool correct: {tool_correct}; "
            f"arguments correct: {args_correct}"
        ),
    }


def evaluate_retrieval(
    retrieved_documents: list[str],
    required_phrase: str,
) -> EvaluationResult:
    """Check whether expected evidence was retrieved."""

    found = any(
        required_phrase.casefold() in document.casefold()
        for document in retrieved_documents
    )

    return {
        "passed": found,
        "score": 1.0 if found else 0.0,
        "reason": (
            "Expected evidence was retrieved."
            if found
            else "Expected evidence was not retrieved."
        ),
    }


def print_result(name: str, result: EvaluationResult) -> None:
    """Print a readable evaluation result."""

    status = "PASS" if result["passed"] else "FAIL"

    print(f"\n[{status}] {name}")
    print(f"Score: {result['score']:.0%}")
    print(f"Reason: {result['reason']}")


if __name__ == "__main__":
    answer_result = evaluate_answer(
        answer="Interstellar was directed by Christopher Nolan.",
        required_keywords=["Christopher Nolan"],
    )

    tool_result = evaluate_tool_call(
        actual_tool="get_movie_details",
        expected_tool="get_movie_details",
        actual_args={"movie_id": 157336},
        expected_args={"movie_id": 157336},
    )

    retrieval_result = evaluate_retrieval(
        retrieved_documents=[
            "CineMind uses TMDB as its movie data source."
        ],
        required_phrase="TMDB",
    )

    print("CineMind Evaluation Demo")

    print_result("Answer quality", answer_result)
    print_result("Tool selection and arguments", tool_result)
    print_result("RAG retrieval", retrieval_result)
