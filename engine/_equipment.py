"""
装备掉落系统 Mixin — 随机掉落、装备到英雄、背包管理。
"""
import random
from config import EQUIP_TIERS, EQUIP_NAMES, BACKPACK_LIMIT


class _EquipmentMixin:
    """提供给 GameEngine 的装备掉落相关方法。"""

    state: object

    def _try_equip_drop(self):
        if len(self.state.equipment_inventory) >= BACKPACK_LIMIT:
            return
        for tier in EQUIP_TIERS:
            if random.random() < tier["drop_per_tick"]:
                rarity = tier["rarity"]
                names = EQUIP_NAMES.get(rarity, ["未知装备"])
                name = random.choice(names)
                bonus = random.randint(tier["bonus_min"], tier["bonus_max"])
                eq = {
                    "name": name, "rarity": rarity,
                    "bonus": bonus, "color": tier["color"],
                }
                self.state.equipment_inventory.append(eq)
                break

    def equip_to_hero(self, eq_index: int, hero_key: str) -> str | None:
        if eq_index < 0 or eq_index >= len(self.state.equipment_inventory):
            return "无效装备"
        hstate = self.state.heroes.get(hero_key)
        if not hstate or hstate["level"] <= 0:
            return "英雄未解锁"
        eq = self.state.equipment_inventory.pop(eq_index)
        old_eq = hstate.get("equipped")
        if old_eq:
            self.state.equipment_inventory.append(old_eq)
        hstate["equipped"] = eq
        self._recalc()
        return None

    def get_equipment(self) -> list:
        return self.state.equipment_inventory
