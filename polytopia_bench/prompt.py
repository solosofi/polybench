import json
from typing import Any, Dict

ACTION_SCHEMA_SUMMARY = (
    "Action JSON schema (output JSON only):\n"
    "- end_turn: { \"type\": \"end_turn\" }\n"
    "- move: { \"type\": \"move\", \"unit_id\": {\"x\":0,\"y\":0}, \"to\": {\"x\":0,\"y\":0} }\n"
    "- attack: { \"type\": \"attack\", \"unit_id\": {\"x\":0,\"y\":0}, \"target\": {\"x\":0,\"y\":0} }\n"
    "- train: { \"type\": \"train\", \"city_id\": {\"x\":0,\"y\":0}, \"unit_type\": \"...\" }\n"
    "- build: { \"type\": \"build\", \"city_id\": {\"x\":0,\"y\":0}, \"building_type\": \"...\" }\n"
    "- research: { \"type\": \"research\", \"tech\": \"...\" }\n"
)


def render_prompt(state: Dict[str, Any]) -> str:
    state_json = json.dumps(state, indent=2, sort_keys=True)
    return (
        "You are playing The Battle of Polytopia.\n"
        "Return ONE action as JSON only. No prose.\n\n"
        f"{ACTION_SCHEMA_SUMMARY}\n"
        "Current state:\n"
        f"{state_json}\n"
    )
