"""
转生与挑战系统 Mixin — 转生重置、挑战模式、声望商店。
"""
import time
from config import PRESTIGE_UPGRADES, CHALLENGES
from .state import GameState
from .types import ChallengeDef, PrestigeUpgradeDef


class _PrestigeMixin:
    """提供给 GameEngine 的转生与挑战相关方法。"""

    state: GameState
    _skill_cooldowns: dict
    _skill_active_until: dict
    _crit_charges: int
    _crit_mult: float
    _auto_click_remaining: float
    _auto_click_rate: float
    _active_dps_mult: float
    _active_click_mult: float
    _golden_buff_active: bool
    _golden_buff_remaining: float
    _golden_button_visible: bool
    _golden_button_timer: float
    _equip_drop_timer: float

    def get_challenges(self) -> list:
        return CHALLENGES

    def get_active_challenge(self) -> ChallengeDef | None:
        """公开查询当前活跃的挑战。"""
        return self._get_challenge()

    def _get_challenge(self) -> ChallengeDef | None:
        if not self.state.active_challenge:
            return None
        for ch in CHALLENGES:
            if ch["key"] == self.state.active_challenge:
                return ch
        return None

    def start_challenge(self, challenge_key: str) -> str | None:
        ch = None
        for c in CHALLENGES:
            if c["key"] == challenge_key:
                ch = c
                break
        if ch is None:
            return "未知挑战"
        self._do_prestige_reset()
        self.state.active_challenge = challenge_key
        self.state.challenge_start_time = time.time()
        self.state.challenge_completed = False
        self._update_era()
        self._recalc()
        return None

    def get_prestige_formula(self) -> int:
        base = int(self.state.total_gold ** (1 / 3) + 0.5)
        mult = 1.0
        ch = self._get_challenge()
        if ch and self.state.challenge_completed:
            mult = ch.get("prestige_mult", 1.0)
        return max(int(base * mult), 1)

    def prestige(self) -> str | None:
        if self.state.total_gold < 1000:
            return "总收益太低，需要至少 1000 金币才能转生"
        pts = self.get_prestige_formula()
        self.state.prestige_points += pts
        self._do_prestige_reset()
        self._update_era()
        self._recalc()
        return None

    def _do_prestige_reset(self):
        """重置游戏进度，保留声望。"""
        pts = self.state.prestige_points
        p_upgs = dict(self.state.prestige_upgrades)
        self.state = GameState()
        self.state.prestige_points = pts
        self.state.prestige_upgrades = p_upgs
        self._init_state()
        self._init_heroes()
        self._equip_drop_timer = 0.0
        self._skill_cooldowns = {k: 0.0 for k in self._skill_cooldowns}
        self._skill_active_until = {k: 0.0 for k in self._skill_active_until}
        self._crit_charges = 0
        self._crit_mult = 1.0
        self._auto_click_remaining = 0.0
        self._auto_click_rate = 0.0
        self._active_dps_mult = 1.0
        self._active_click_mult = 1.0
        self._golden_buff_active = False
        self._golden_buff_remaining = 0.0
        self._golden_button_visible = False
        self._golden_button_timer = 0.0
        self._schedule_golden_button()
        # 声望起始金币
        for pdef in PRESTIGE_UPGRADES:
            lv = self.state.prestige_upgrades.get(pdef["key"], 0)
            if lv > 0 and pdef["effect_type"] == "start_gold":
                self.state.gold += int(pdef["effect_per_level"] * lv)

    def get_prestige_upgrades(self) -> list:
        return PRESTIGE_UPGRADES

    def buy_prestige_upgrade(self, key: str) -> str | None:
        pdef = None
        for pd in PRESTIGE_UPGRADES:
            if pd["key"] == key:
                pdef = pd
                break
        if pdef is None:
            return "未知声望升级"
        cur_lv = self.state.prestige_upgrades.get(key, 0)
        if cur_lv >= pdef["max_level"]:
            return "已达最大等级"
        cost = pdef["cost"] * (cur_lv + 1)
        if self.state.prestige_points < cost:
            return f"声望不足 (需要 {cost})"
        self.state.prestige_points -= cost
        self.state.prestige_upgrades[key] = cur_lv + 1
        self._recalc()
        return None
