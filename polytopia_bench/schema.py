import json
from typing import Any, Dict

REQUIRED_STATE_KEYS = {"turn", "player", "cities", "units", "tech", "map"}

ACTION_SPECS = {
    "end_turn": {"required": set(), "optional": set()},
    "move": {"required": {"unit_id", "to"}, "optional": {"from"}},
    "attack": {"required": {"unit_id", "target"}, "optional": {"from"}},
    "train": {"required": {"city_id", "unit_type"}, "optional": set()},
    "build": {"required": {"city_id", "building_type"}, "optional": set()},
    "research": {"required": {"tech"}, "optional": set()},
}


def validate_state(state: Dict[str, Any]) -> None:
    if not isinstance(state, dict):
        raise ValueError("State must be a JSON object")
    missing = REQUIRED_STATE_KEYS - set(state.keys())
    if missing:
        raise ValueError(f"State missing required keys: {sorted(missing)}")


def _require_pos(name: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object with x,y")
    if "x" not in value or "y" not in value:
        raise ValueError(f"{name} must include x and y")


def _maybe_require_xy(name: str, value: Any) -> None:
    if isinstance(value, dict):
        _require_pos(name, value)


def validate_action(action: Dict[str, Any]) -> None:
    if not isinstance(action, dict):
        raise ValueError("Action must be a JSON object")
    action_type = action.get("type")
    if action_type not in ACTION_SPECS:
        raise ValueError(f"Unknown action type: {action_type}")

    spec = ACTION_SPECS[action_type]
    required = spec["required"]
    optional = spec["optional"]
    allowed = set(required) | set(optional) | {"type"}

    extra = set(action.keys()) - allowed
    if extra:
        raise ValueError(f"Action has unknown fields: {sorted(extra)}")

    missing = required - set(action.keys())
    if missing:
        raise ValueError(f"Action missing required fields: {sorted(missing)}")

    if action_type == "move":
        _require_pos("to", action["to"])
        _maybe_require_xy("unit_id", action.get("unit_id"))
    if action_type == "attack":
        # target can be id or position, but must be present
        if isinstance(action["target"], dict):
            _require_pos("target", action["target"])
        _maybe_require_xy("unit_id", action.get("unit_id"))
    if action_type in ("train", "build", "research", "move", "attack"):
        # no additional validation required
        return


def extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in LLM response")
    return text[start : end + 1]


def parse_action(text: str) -> Dict[str, Any]:
    try:
        action = json.loads(text)
    except json.JSONDecodeError:
        action = json.loads(extract_json_object(text))
    validate_action(action)
    return action
