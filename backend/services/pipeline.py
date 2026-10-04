"""Hiring pipeline: which status changes are allowed."""

# Status values are shown to the client, so they stay in Spanish
TRANSITIONS = {
    "nuevo": {"preseleccionado", "rechazado"},
    "preseleccionado": {"entrevista", "rechazado"},
    "entrevista": {"oferta", "rechazado"},
    "oferta": {"contratado", "rechazado"},
    "contratado": set(),
    "rechazado": set(),
}


def is_valid_transition(current: str, new: str) -> bool:
    return new in TRANSITIONS.get(current, set())


def next_statuses(current: str) -> list[str]:
    return sorted(TRANSITIONS.get(current, set()))
