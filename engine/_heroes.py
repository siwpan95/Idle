"""
英雄系统 Mixin — 英雄招募、升级、装备。
"""
from config import HEROES
from .types import HeroDef, HeroState


class _HeroesMixin:
    """提供给 GameEngine 的英雄相关方法。"""

    state: object

    def _init_heroes(self):
        for h in HEROES:
            if h["key"] not in self.state.heroes:
                self.state.heroes[h["key"]] = {"level": 0, "equipped": None}

    def get_heroes(self) -> list:
        return HEROES

    def get_hero_info(self, key: str) -> HeroDef | None:
        """公开查询英雄定义。"""
        for h in HEROES:
            if h["key"] == key:
                return h
        return None

    def get_hero_state(self, key: str) -> HeroState:
        return self.state.heroes.get(key, {"level": 0, "equipped": None})

    def unlock_hero(self, key: str) -> str | None:
        hdef = self.get_hero_info(key)
        if not hdef:
            return "未知英雄"
        hstate = self.state.heroes.get(key, {"level": 0})
        if hstate["level"] > 0:
            return "已解锁"
        if self.state.gold < hdef["unlock_gold"]:
            return f"需要 {self.fmt_gold(hdef['unlock_gold'])} 金币"
        self.state.gold -= hdef["unlock_gold"]
        self.state.heroes[key] = {"level": 1, "equipped": None}
        self._recalc()
        return None

    def upgrade_hero(self, key: str) -> str | None:
        hdef = self.get_hero_info(key)
        if not hdef:
            return "未知英雄"
        hstate = self.state.heroes.get(key, {"level": 0})
        if hstate["level"] <= 0:
            return "未解锁"
        if hstate["level"] >= hdef["max_level"]:
            return "已达最大等级"
        cost = int(hdef["upgrade_cost"] * (hdef["upgrade_mult"] ** (hstate["level"] - 1)))
        if self.state.gold < cost:
            return f"需要 {self.fmt_gold(cost)} 金币"
        self.state.gold -= cost
        self.state.heroes[key]["level"] = hstate["level"] + 1
        self._recalc()
        return None

    def get_hero_upgrade_cost(self, key: str) -> int:
        hdef = self.get_hero_info(key)
        if not hdef:
            return 0
        hstate = self.state.heroes.get(key, {"level": 0})
        if hstate["level"] <= 0:
            return hdef["unlock_gold"]
        return int(hdef["upgrade_cost"] * (hdef["upgrade_mult"] ** (hstate["level"] - 1)))
