"""Hiring pipeline: which status changes are allowed."""

TRANSITIONS = {
    "new": {"shortlisted", "rejected"},
    "shortlisted": {"interview", "rejected"},
    "interview": {"offer", "rejected"},
    "offer": {"hired", "rejected"},
    "hired": set(),
    "rejected": set(),
}

# Spanish names used in the messages shown to the user
STATUS_LABELS = {
    "new": "nuevo",
    "shortlisted": "preseleccionado",
    "interview": "entrevista",
    "offer": "oferta",
    "hired": "contratado",
    "rejected": "rechazado",
}


def is_valid_transition(current: str, new: str) -> bool:
    return new in TRANSITIONS.get(current, set())


def next_statuses(current: str) -> list[str]:
    return [s for s in TRANSITIONS if s in TRANSITIONS.get(current, set())]
