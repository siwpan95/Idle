"""
核心计算 Mixin — 装备加载、DPS/点击力计算、初始化。
"""
from config import UPGRADE_DEFS, SKILLS, PRESTIGE_UPGRADES, HEROES, ERAS
from .upgrade import UpgradeDef


class _CalcMixin:
    """提供给 GameEngine 的 DPS 计算和装备加载方法。"""

    state: object
    _defs: dict
    _dps_gears: list
    _era_index: int
    _skill_cooldowns: dict
    _skill_active_until: dict
    _active_dps_mult: float
    _active_click_mult: float
    _golden_buff_active: bool
    _golden_buff_remaining: float

    def _load_defs(self):
        for raw in UPGRADE_DEFS:
            d = UpgradeDef(raw)
            self._defs[d.key] = d
            if d.per_second > 0:
                self._dps_gears.append(d)
        # 解析 JSON 中的字符串引用为对象引用
        for d in self._defs.values():
            if isinstance(d.multiplier, str):
                d.multiplier = self._defs.get(d.multiplier)
            if isinstance(d.synergy_unlocked, str):
                d.synergy_unlocked = self._defs.get(d.synergy_unlocked)
            if isinstance(d.synergy_building, str):
                d.synergy_building = self._defs.get(d.synergy_building)
            if isinstance(d.power_gear, str):
                d.power_gear = self._defs.get(d.power_gear)
            if isinstance(d.empowers, str):
                d.empowers = self._defs.get(d.empowers)

    def _init_state(self):
        for key in self._defs:
            self.state.upgrades.setdefault(key, 0)
            self.state.empowered.setdefault(key, 0)
        for sk in SKILLS:
            self._skill_cooldowns.setdefault(sk["key"], 0.0)
            self._skill_active_until.setdefault(sk["key"], 0.0)
        for pk in PRESTIGE_UPGRADES:
            self.state.prestige_upgrades.setdefault(pk["key"], 0)

    # ==================== 前置条件 ====================
    def check_prerequisite(self, defn: UpgradeDef) -> bool:
        if defn.requires is None:
            return True
        req_key, req_level = defn.requires
        return self.state.upgrades.get(req_key, 0) >= req_level

    def get_prerequisite_text(self, defn: UpgradeDef) -> str:
        if defn.requires is None:
            return ""
        req_key, req_level = defn.requires
        req_name = self._defs[req_key].name if req_key in self._defs else req_key
        if req_level == 0:
            return f"需要解锁: {req_name}"
        return f"需要: {req_name} {req_level}级"

    # ==================== 核心计算 ====================
    def _recalc(self):
        from config import GOLDEN_BUFF

        challenge = self._get_challenge()
        restrict_dps = challenge and challenge.get("restrict_dps")

        # ---- 基础 DPS ----
        dps = self._calc_base_dps(restrict_dps)

        # ---- 协同效应 ----
        if not restrict_dps:
            dps = self._apply_synergies(dps)

        # ---- 力量联动 ----
        if not restrict_dps:
            dps = self._apply_power_gear(dps)

        # ---- 全局 CPS 乘数 ----
        if not restrict_dps:
            dps *= 1.01 ** self.state.upgrades.get("cps_multiplier", 0)

        # ---- 纪元加成 ----
        era = self.get_current_era()
        dps *= era["bonus_dps"]

        # ---- 声望加成 ----
        dps = self._apply_prestige_dps(dps)

        # ---- 技能加成 ----
        dps *= self._active_dps_mult

        # ---- 英雄加成 ----
        dps = self._apply_hero_dps(dps)

        self.state.dps = dps

        # ---- 点击力 ----
        self.state.click_power = self._calc_click_power(dps, era, challenge)

    def _calc_base_dps(self, restrict_dps: bool) -> float:
        """计算基础 DPS（不含协同/纪元/声望/技能/英雄加成）。"""
        if restrict_dps:
            return 0.0
        base = 0.0
        for d in self._dps_gears:
            qty = self.state.upgrades[d.key]
            if qty <= 0:
                continue
            mult = 2 ** self.state.upgrades.get(d.multiplier.key, 0) if d.multiplier else 1
            emp_pow = self.state.empowered.get(d.key, 0)
            base += d.per_second * qty * mult * (2 ** emp_pow)
        return base

    def _apply_synergies(self, base_dps: float) -> float:
        """应用协同效应加成。"""
        result = base_dps
        for d in self._defs.values():
            if d.synergy_unlocked and d.synergy_building:
                unlock_qty = self.state.upgrades.get(d.synergy_unlocked.key, 0)
                if unlock_qty > 0:
                    my_qty = self.state.upgrades.get(d.key, 0)
                    partner_qty = self.state.upgrades.get(d.synergy_building.key, 0)
                    result += my_qty * partner_qty * 0.05 * base_dps
        return result

    def _apply_power_gear(self, base_dps: float) -> float:
        """应用力量联动加成。"""
        result = base_dps
        for d in self._defs.values():
            if d.power_gear and d.empowers:
                my_qty = self.state.upgrades.get(d.key, 0)
                if my_qty <= 0:
                    continue
                src_qty = self.state.upgrades.get(d.power_gear.key, 0)
                tgt_qty = self.state.upgrades.get(d.empowers.key, 0)
                if src_qty > 0 and tgt_qty > 0:
                    result += src_qty * tgt_qty * base_dps * 0.05
        return result

    def _apply_prestige_dps(self, dps: float) -> float:
        """应用声望 DPS 加成。"""
        result = dps
        for pdef in PRESTIGE_UPGRADES:
            lv = self.state.prestige_upgrades.get(pdef["key"], 0)
            if lv > 0 and pdef["effect_type"] == "dps_mult":
                result *= 1 + (pdef["effect_per_level"] * lv)
        return result

    def _apply_hero_dps(self, dps: float) -> float:
        """应用英雄 DPS 加成（被动 + 装备）。"""
        result = dps
        for hero_key, hstate in self.state.heroes.items():
            hdef = self.get_hero_info(hero_key)
            if hdef and hstate["level"] > 0:
                bonus = hdef.get("passive_dps_bonus", 0)
                if bonus:
                    result *= 1 + (bonus * hstate["level"])
                eq = hstate.get("equipped")
                if eq:
                    result += eq.get("bonus", 0)
        return result

    def _calc_click_power(self, dps: float, era: dict, challenge) -> float:
        """计算点击力。"""
        from config import GOLDEN_BUFF

        challenge_restrict_click = challenge and challenge.get("restrict_click")
        if challenge_restrict_click:
            return 0

        cp = 1.0
        cp += self.state.upgrades.get("clicker", 0)
        cp += self.state.upgrades.get("mobster", 0) * sum(
            self.state.upgrades[d.key] for d in self._dps_gears
        )
        cp += self.state.upgrades.get("cps_to_click", 0) * 0.01 * dps
        cp *= 2 ** self.state.upgrades.get("click_booster", 0)

        if self._golden_buff_active:
            cp *= GOLDEN_BUFF["strength"]

        cp *= era["bonus_click"]

        for pdef in PRESTIGE_UPGRADES:
            lv = self.state.prestige_upgrades.get(pdef["key"], 0)
            if lv > 0 and pdef["effect_type"] == "click_mult":
                cp *= 1 + (pdef["effect_per_level"] * lv)

        cp *= self._active_click_mult

        for hero_key, hstate in self.state.heroes.items():
            hdef = self.get_hero_info(hero_key)
            if hdef and hstate["level"] > 0:
                bonus = hdef.get("passive_click_bonus", 0)
                if bonus:
                    cp *= 1 + (bonus * hstate["level"])

        return int(cp)
