import os
import time
from pathlib import Path

from dotenv import dotenv_values
from pymongo import MongoClient

_CACHE_TTL_SECONDS = 60
_STOP_WORDS = {
    "the", "and", "what", "which", "where", "when", "should", "could", "would", "from",
    "with", "about", "are", "is", "in", "my", "i", "a", "an", "to", "of", "for", "do",
}
_OVERVIEW_TERMS = {
    "how many", "number of", "list", "all phases", "phase names", "curriculum overview",
    "learning path", "roadmap", "course structure", "what phases",
}
_cached_curriculum = None
_cached_at = 0
_mongo_client = None


def _get_mongo_uri():
    configured_uri = os.getenv("PHASETRACKER_MONGO_URI")
    if configured_uri:
        return configured_uri

    env_path = os.getenv(
        "PHASETRACKER_ENV_FILE",
        str(Path(__file__).resolve().parents[3] / "phasetracker" / "backend" / ".env"),
    )
    values = dotenv_values(env_path)
    return values.get("MONGO_URI")


def _get_database():
    global _mongo_client
    mongo_uri = _get_mongo_uri()
    if not mongo_uri:
        raise RuntimeError("PhaseTracker MongoDB URI is not configured")

    if _mongo_client is None:
        _mongo_client = MongoClient(mongo_uri, serverSelectionTimeoutMS=2500, connectTimeoutMS=2500)
    database_name = os.getenv("PHASETRACKER_MONGO_DB", "test")
    database = _mongo_client[database_name]
    _mongo_client.admin.command("ping")
    return database


def _load_curriculum():
    database = _get_database()
    phases = list(database.phases.find(
        {},
        {
            "_id": 0,
            "id": 1,
            "name": 1,
            "description": 1,
            "order": 1,
            "isStarting": 1,
            "isEnding": 1,
        },
    ).sort("order", 1))
    subphases = list(database.subphases.find(
        {},
        {
            "_id": 0,
            "phaseId": 1,
            "id": 1,
            "title": 1,
            "description": 1,
            "order": 1,
            "requirements": 1,
        },
    ).sort([("phaseId", 1), ("order", 1)]))

    grouped_subphases = {}
    for subphase in subphases:
        grouped_subphases.setdefault(subphase.get("phaseId"), []).append(subphase)

    for phase in phases:
        phase["subphases"] = grouped_subphases.get(phase.get("id"), [])
    return phases


def get_curriculum_context(question):
    """Return public curriculum context relevant to a question, or an empty string if unavailable."""
    global _cached_curriculum, _cached_at
    now = time.monotonic()
    try:
        if _cached_curriculum is None or now - _cached_at > _CACHE_TTL_SECONDS:
            _cached_curriculum = _load_curriculum()
            _cached_at = now

        normalized_question = " ".join(question.lower().split())
        question_words = {
            word.strip(".,?!:;()[]{}\"'")
            for word in normalized_question.split()
        } - _STOP_WORDS
        is_overview_question = any(term in normalized_question for term in _OVERVIEW_TERMS)
        wants_details = any(term in normalized_question for term in ("topic", "topics", "project", "projects", "sub-phase", "lesson", "learn"))
        relevant_phases = []
        for phase in _cached_curriculum:
            search_text = " ".join([
                str(phase.get("id", "")),
                str(phase.get("name", "")),
                str(phase.get("description", "")),
            ]).lower()
            if not question_words or any(word in search_text for word in question_words if len(word) > 2):
                relevant_phases.append(phase)

        selected_phases = relevant_phases or _cached_curriculum
        lines = [
            "LIVE PHASETRACKER CURRICULUM (retrieved from MongoDB).",
            f"Total configured phases: {len(_cached_curriculum)}",
            "Phase index:",
        ]
        for phase in _cached_curriculum:
            flags = []
            if phase.get("isStarting"):
                flags.append("starting")
            if phase.get("isEnding"):
                flags.append("ending")
            marker = f" ({', '.join(flags)})" if flags else ""
            raw_order = phase.get("order")
            display_order = raw_order + 1 if isinstance(raw_order, (int, float)) else raw_order
            lines.append(f"Phase {display_order}: {phase.get('name', phase.get('id', 'Unnamed'))}{marker}")

        if wants_details:
            lines.append("Relevant phase details:")
        for phase in selected_phases[:8] if wants_details else []:
            if phase.get("description"):
                lines.append(f"Description: {phase['description']}")
            for subphase in phase.get("subphases", [])[:12]:
                requirements = subphase.get("requirements") or {}
                requirement_names = [name for name, enabled in requirements.items() if enabled]
                requirement_text = f"; requirements: {', '.join(requirement_names)}" if requirement_names else ""
                lines.append(f"- {subphase.get('title', subphase.get('id', 'Untitled'))}: {subphase.get('description', '')}{requirement_text}")
        return "\n".join(lines)[:7000]
    except Exception as error:
        print(f"Curriculum context unavailable: {error}", flush=True)
        return ""
