"""
游戏状态 — dataclass，可序列化/反序列化，存档兼容。
"""

import time
from dataclasses import dataclass, field


@dataclass
class GameState:
    gold: float = 0.0
    total_gold: float = 0.0
    dps: float = 0.0
    click_power: float = 1.0
    upgrades: dict = field(default_factory=dict)
    empowered: dict = field(default_factory=dict)
    last_tick: float = 0.0
    prestige_points: int = 0
    prestige_upgrades: dict = field(default_factory=dict)
    active_challenge: str | None = None
    challenge_start_time: float = 0.0
    challenge_completed: bool = False
    heroes: dict = field(default_factory=dict)
    equipment_inventory: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "gold": self.gold,
            "total_gold": self.total_gold,
            "dps": self.dps,
            "click_power": self.click_power,
            "upgrades": dict(self.upgrades),
            "empowered": dict(self.empowered),
            "prestige_points": self.prestige_points,
            "prestige_upgrades": dict(self.prestige_upgrades),
            "active_challenge": self.active_challenge,
            "challenge_start_time": self.challenge_start_time,
            "challenge_completed": self.challenge_completed,
            "heroes": dict(self.heroes),
            "equipment_inventory": list(self.equipment_inventory),
            "ts": time.time(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GameState":
        s = cls()
        s.gold = d.get("gold", 0)
        s.total_gold = d.get("total_gold", 0)
        s.dps = d.get("dps", 0)
        s.click_power = d.get("click_power", 1)
        s.upgrades = d.get("upgrades", {})
        s.empowered = d.get("empowered", {})
        s.prestige_points = d.get("prestige_points", 0)
        s.prestige_upgrades = d.get("prestige_upgrades", {})
        s.active_challenge = d.get("active_challenge")
        s.challenge_start_time = d.get("challenge_start_time", 0)
        s.challenge_completed = d.get("challenge_completed", False)
        s.heroes = d.get("heroes", {})
        s.equipment_inventory = d.get("equipment_inventory", [])
        return s
