from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict

from .adapters import UIAutomationAdapter


class GameAPI(ABC):
    @abstractmethod
    def reset(self, difficulty: str, opponents: int, game_index: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def get_state(self) -> Dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def apply_action(self, action: Dict[str, Any], run_dir: str, turn_index: int) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_done(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def get_result(self) -> Dict[str, Any]:
        raise NotImplementedError


class UIAutomationGameAPI(GameAPI):
    def __init__(self, calibration_path: str = "calibration.json") -> None:
        self._adapter = UIAutomationAdapter(calibration_path)

    def reset(self, difficulty: str, opponents: int, game_index: int) -> None:
        self._adapter.reset(difficulty, opponents, game_index)

    def get_state(self) -> Dict[str, Any]:
        return self._adapter.get_state()

    def apply_action(self, action: Dict[str, Any], run_dir: str, turn_index: int) -> None:
        self._adapter.apply_action(action, run_dir, turn_index)

    def is_done(self) -> bool:
        return self._adapter.is_done()

    def get_result(self) -> Dict[str, Any]:
        return self._adapter.get_result()
