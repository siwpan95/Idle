"""
存档系统 Mixin — 游戏进度保存与加载。
"""
import json
import os
import time
from config import SAVE_FILE, PRESTIGE_UPGRADES
from .state import GameState


class _PersistenceMixin:
    """提供给 GameEngine 的存档相关方法。"""

    state: GameState
    _defs: dict

    def save(self):
        with open(SAVE_FILE, "w", encoding="utf-8") as f:
            json.dump(self.state.to_dict(), f)

    def _load(self):
        if not os.path.exists(SAVE_FILE):
            return
        with open(SAVE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        loaded = GameState.from_dict(data)
        for key in self._defs:
            loaded.upgrades.setdefault(key, 0)
            loaded.empowered.setdefault(key, 0)
        for pk in PRESTIGE_UPGRADES:
            loaded.prestige_upgrades.setdefault(pk["key"], 0)
        self.state = loaded
        self.state.last_tick = time.time()
