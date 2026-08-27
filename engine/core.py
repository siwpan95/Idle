"""
游戏核心引擎 — 组装所有 Mixin，对外暴露统一的 GameEngine 接口。
"""

import time
from config import (
    UPGRADE_DEFS, SKILLS, GOLDEN_BUFF, TICK_DT_MAX,
)
from .state import GameState
from .upgrade import UpgradeDef
from .fmt import fmt_gold, fmt_dps, fmt_num
from ._era import _EraMixin
from ._calc import _CalcMixin
from ._skills import _SkillsMixin
from ._heroes import _HeroesMixin
from ._prestige import _PrestigeMixin
from ._persistence import _PersistenceMixin
from ._golden import _GoldenMixin
from ._equipment import _EquipmentMixin


class GameEngine(
    _EraMixin,
    _CalcMixin,
    _SkillsMixin,
    _HeroesMixin,
    _PrestigeMixin,
    _PersistenceMixin,
    _GoldenMixin,
    _EquipmentMixin,
):
    """放置英雄核心引擎。"""

    def __init__(self):
        self.state = GameState()
        self._defs: dict[str, UpgradeDef] = {}
        self._dps_gears: list[UpgradeDef] = []

        # 纪元
        self._era_index: int = 0

        # 技能状态
        self._skill_cooldowns: dict[str, float] = {}
        self._skill_active_until: dict[str, float] = {}
        self._crit_charges: int = 0
        self._crit_mult: float = 1.0
        self._auto_click_remaining: float = 0.0
        self._auto_click_rate: float = 0.0
        self._active_dps_mult: float = 1.0
        self._active_click_mult: float = 1.0

        # 黄金按钮
        self._golden_buff_active = False
        self._golden_buff_remaining = 0.0
        self._golden_button_visible = False
        self._golden_button_timer = 0.0

        self._load_defs()
        self._init_state()
        self._init_heroes()
        self._equip_drop_timer: float = 0.0
        self._load()
        self._update_era()
        self._recalc()
        self._schedule_golden_button()

    # ==================== 操作 ====================

    def click(self) -> int:
        gain = self.state.click_power
        if self._crit_charges > 0:
            gain = int(gain * self._crit_mult)
            self._crit_charges -= 1
            if self._crit_charges <= 0:
                self._crit_mult = 1.0
        self.state.gold += gain
        self.state.total_gold += gain
        return gain

    def tick(self, now: float) -> float:
        dt = now - self.state.last_tick
        self.state.last_tick = now
        if dt > TICK_DT_MAX:
            dt = TICK_DT_MAX

        # DPS 产金
        self.state.gold += self.state.dps * dt
        self.state.total_gold += self.state.dps * dt

        # 装备掉落检测
        self._equip_drop_timer += dt
        if self._equip_drop_timer >= 1.0:
            self._equip_drop_timer -= 1.0
            self._try_equip_drop()

        # 主动技能倒计时
        for sk in SKILLS:
            key = sk["key"]
            if self._skill_cooldowns.get(key, 0) > 0:
                self._skill_cooldowns[key] = max(0, self._skill_cooldowns[key] - dt)
            if self._skill_active_until.get(key, 0) > 0:
                self._skill_active_until[key] -= dt
                if self._skill_active_until[key] <= 0:
                    self._deactivate_skill(key)

        # 自动点击
        if self._auto_click_remaining > 0:
            self._auto_click_remaining -= dt
            gold_per_tick = self.state.click_power * self._auto_click_rate * dt
            self.state.gold += gold_per_tick
            self.state.total_gold += gold_per_tick
            if self._auto_click_remaining <= 0:
                self._auto_click_rate = 0.0

        # 黄金 buff
        if self._golden_buff_active:
            self._golden_buff_remaining -= dt
            if self._golden_buff_remaining <= 0:
                self._golden_buff_active = False
                self._recalc()

        # 黄金按钮
        if not self._golden_button_visible:
            self._golden_button_timer -= dt
            if self._golden_button_timer <= 0:
                if self.state.upgrades.get("golden_click", 0) > 0:
                    self._golden_button_visible = True
                    self._golden_button_timer = GOLDEN_BUFF["button_duration"]
        if self._golden_button_visible:
            self._golden_button_timer -= dt
            if self._golden_button_timer <= 0:
                self._golden_button_visible = False
                self._schedule_golden_button()

        # 挑战时间限制
        challenge = self._get_challenge()
        if challenge and challenge.get("time_limit"):
            elapsed = now - self.state.challenge_start_time
            target_era_key = challenge["target_era"]
            if self.is_era_unlocked(target_era_key):
                self.state.challenge_completed = True
            elif elapsed > challenge["time_limit"]:
                self.state.challenge_completed = False

        # 纪元检测
        old_era = self._era_index
        self._update_era()
        if self._era_index != old_era:
            self._recalc()

        return dt

    # ==================== 购买 ====================

    def get_cost(self, key: str) -> int:
        d = self._defs.get(key)
        if not d:
            return 0
        return d.get_cost(self.state.upgrades.get(key, 0))

    def can_buy(self, key: str) -> bool:
        d = self._defs.get(key)
        if not d:
            return False
        if not d.can_buy(self.state.upgrades.get(key, 0)):
            return False
        if not self.is_era_unlocked(d.era):
            return False
        if not self.check_prerequisite(d):
            return False
        if d.per_second > 0:
            challenge = self._get_challenge()
            if challenge and challenge.get("restrict_dps"):
                return False
        return self.state.gold >= d.get_cost(self.state.upgrades.get(key, 0))

    def buy(self, key: str) -> str | None:
        d = self._defs.get(key)
        if d is None:
            return "未知升级"
        qty = self.state.upgrades.get(key, 0)
        if not d.can_buy(qty):
            return f"{d.name} 已达上限"
        if not self.is_era_unlocked(d.era):
            return f"{d.name} 尚未在当前纪元解锁"
        if not self.check_prerequisite(d):
            return self.get_prerequisite_text(d)
        challenge = self._get_challenge()
        if d.per_second > 0 and challenge and challenge.get("restrict_dps"):
            return "当前挑战禁用 DPS 装备"
        cost = d.get_cost(qty)
        if self.state.gold < cost:
            return f"{d.name} 需要 {fmt_gold(cost)} 金币"
        self.state.gold -= cost
        self.state.upgrades[key] = qty + 1
        if d.empowers:
            self.state.empowered[d.empowers.key] += 1
        if d.callback == "golden":
            self._activate_golden()
        self._recalc()
        return None

    # ==================== 可见/分类 ====================

    def get_def(self, key: str):
        return self._defs.get(key)

    def get_visible_upgrades(self, category: str = "all") -> list:
        result = []
        for d in self._defs.values():
            if not self.is_era_unlocked(d.era):
                continue
            if category != "all" and d.category != category:
                continue
            qty = self.state.upgrades.get(d.key, 0)
            if d.is_visible(self.state.total_gold, qty):
                result.append(d)
        result.sort(key=lambda x: x.get_cost(self.state.upgrades.get(x.key, 0)))
        return result
