"""
入口模块 — 装配引擎与 UI，启动游戏循环
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import time
from config import WINDOW_WIDTH, WINDOW_HEIGHT, COLOR_BG, GAME_LOOP_MS
from engine import GameEngine
from ui import GameUI


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("放置英雄")
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=COLOR_BG)

        self.engine = GameEngine()

        self.ui = GameUI(
            self.root,
            on_buy=self._on_buy,
            on_click=self._on_click,
            on_skill=self._on_skill,
            on_prestige=self._on_prestige_menu,
            on_hero=self._on_hero,
        )
        self._full_draw()

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._last_tick = time.time()
        self._game_loop()

    # ==================== 事件 ====================
    def _on_click(self, ev=None):
        ch = self.engine.get_active_challenge()
        if ch and ch.get("restrict_click"):
            return
        gain = self.engine.click()
        self.ui.spawn_float(f"+{gain}")

    def _on_buy(self, key):
        err = self.engine.buy(key)
        if err:
            messagebox.showinfo("无法购买", err)

    def _on_skill(self, key):
        err = self.engine.activate_skill(key)
        if err:
            messagebox.showinfo("技能", err)

    def _on_hero(self, action, hero_key):
        if action == "upgrade":
            hstate = self.engine.get_hero_state(hero_key)
            if hstate["level"] <= 0:
                err = self.engine.unlock_hero(hero_key)
            else:
                err = self.engine.upgrade_hero(hero_key)
            if err:
                messagebox.showinfo("英雄", err)

    def _on_prestige_menu(self):
        pts = self.engine.state.prestige_points
        f = self.engine.get_prestige_formula()
        choice = simpledialog.askstring("转生",
            f"声望: {pts} | 转生获 {f}\n\n1.转生  2.挑战  3.声望商店  4.装备英雄")
        if not choice:
            return
        if choice == "1":
            if self.ui.show_prestige_dialog(self.engine):
                err = self.engine.prestige()
                if err:
                    messagebox.showinfo("转生", err)
                else:
                    self._full_draw()
                    messagebox.showinfo("转生", f"获得 {f} 声望")
        elif choice == "2":
            k = self.ui.show_challenge_dialog(self.engine)
            if k:
                err = self.engine.start_challenge(k)
                if err:
                    messagebox.showinfo("挑战", err)
                else:
                    self._full_draw()
        elif choice == "3":
            self.ui.show_prestige_shop(self.engine)
        elif choice == "4":
            self._equip_menu()

    def _equip_menu(self):
        eqs = self.engine.get_equipment()
        if not eqs:
            messagebox.showinfo("装备", "背包为空")
            return
        lines = [f"[{i+1}] {eq['name']} +{eq['bonus']} ({eq['rarity']})"
                 for i, eq in enumerate(eqs[-8:])]
        heroes = self.engine.get_heroes()
        hl = "\n".join(f"{j+1}. {h['name']} {self.engine.get_hero_state(h['key'])['level']}级"
                       for j, h in enumerate(heroes))
        r = simpledialog.askstring("装备英雄",
            "\n".join(lines) + "\n\n" + hl + "\n\n装备编号,英雄编号:")
        if r:
            parts = r.replace(" ", "").split(",")
            if len(parts) == 2 and parts[0].isdigit() and parts[1].isdigit():
                ei, hi = int(parts[0]) - 1, int(parts[1]) - 1
                if 0 <= hi < len(heroes):
                    err = self.engine.equip_to_hero(ei, heroes[hi]["key"])
                    if err:
                        messagebox.showinfo("装备", err)

    # ==================== 绘制 ====================
    def _full_draw(self):
        self.ui.draw_hud(self.engine.state.gold, self.engine.state.dps)
        self.ui.draw_shop_buttons(self.engine)
        self.ui.update_era_bar(self.engine)
        self.ui.update_skill_buttons(self.engine)
        self.ui.update_hero_panel(self.engine)
        self.ui.update_equipment_bar(self.engine)

    def _game_loop(self):
        now = time.time()
        dt = now - self._last_tick
        self.engine.tick(now)

        self.ui.refresh_hud(self.engine.state.gold, self.engine.state.dps)
        self.ui.update_floaters(dt)
        self.ui.update_era_bar(self.engine)
        self.ui.update_skill_buttons(self.engine)
        self.ui.update_hero_panel(self.engine)
        self.ui.update_equipment_bar(self.engine)
        self.ui.update_golden_timer(
            self.engine.golden_buff_remaining,
            self.engine.golden_buff_active
        )
        self.ui.refresh_shop_if_needed(self.engine)
        self.ui.refresh_shop_buttons(self.engine)

        self._last_tick = now
        self.root.after(GAME_LOOP_MS, self._game_loop)

    def _on_close(self):
        self.engine.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
