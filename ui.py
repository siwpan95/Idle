"""
渲染层 — 三区布局：顶栏(纪元+HUD+标签) | 左商店+右面板 | 底栏(装备+声望)
使用本地思源黑体字体。
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import random
import time
from config import *
from fonts import get_font


class GameUI:
    def __init__(self, root: tk.Tk,
                 on_buy, on_click, on_skill, on_prestige, on_hero):
        self._on_buy = on_buy
        self._on_click = on_click
        self._on_skill = on_skill
        self._on_prestige = on_prestige
        self._on_hero = on_hero
        self._active_category = "all"

        self.floaters: list[list] = []

        # ========== 1. 顶栏 ==========
        self._build_top_bar(root)

        # ========== 2. 主体：左商店 + 右面板 ==========
        self._build_main_area(root)

        # ========== 3. 底栏 ==========
        self._build_bottom_bar(root)

        # 所有静态绘制
        self._draw_top_static()
        self._draw_panel_static()
        self._draw_bottom_static()

    # =========================== 构建结构 ===========================

    def _build_top_bar(self, root):
        self.top_cv = tk.Canvas(
            root, width=WINDOW_WIDTH, height=CANVAS_TOP_H,
            bg=COLOR_BG, highlightthickness=0
        )
        self.top_cv.pack(fill=tk.X)

    def _build_main_area(self, root):
        main_frame = tk.Frame(root, bg=COLOR_BG)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # 左：商店
        shop_frame = tk.Frame(main_frame, bg=COLOR_BG)
        shop_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.shop_scroll = tk.Scrollbar(shop_frame, orient=tk.VERTICAL)
        self.shop_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.shop_cv = tk.Canvas(
            shop_frame, bg=COLOR_PANEL, highlightthickness=0,
            yscrollcommand=self.shop_scroll.set
        )
        self.shop_cv.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.shop_scroll.config(command=self.shop_cv.yview)
        self.shop_cv.bind("<MouseWheel>", self._on_mousewheel)

        self._btn_items: dict = {}
        self._visible_keys: set = set()

        # 右：面板
        panel_frame = tk.Frame(main_frame, bg=COLOR_BG, width=PANEL_WIDTH)
        panel_frame.pack(side=tk.RIGHT, fill=tk.Y)
        panel_frame.pack_propagate(False)

        self.panel_cv = tk.Canvas(
            panel_frame, width=PANEL_WIDTH, bg=COLOR_BG, highlightthickness=0
        )
        self.panel_cv.pack(fill=tk.BOTH, expand=True)
        # 面板需要足够高度来画所有内容
        self.panel_cv.config(scrollregion=(0, 0, PANEL_WIDTH, HERO_PANEL_SCROLL_H))

    def _build_bottom_bar(self, root):
        self.bottom_cv = tk.Canvas(
            root, width=WINDOW_WIDTH, height=CANVAS_BOTTOM_H,
            bg="#0c0c1e", highlightthickness=0
        )
        self.bottom_cv.pack(fill=tk.X, side=tk.BOTTOM)

    # =========================== 顶栏绘制 ===========================

    def _draw_top_static(self):
        cv = self.top_cv

        # 纪元进度条
        cv.create_rectangle(
            ERA_BAR_X, ERA_BAR_Y, ERA_BAR_X + ERA_BAR_W, ERA_BAR_Y + ERA_BAR_H,
            fill=COLOR_ERA_BAR_BG, outline="", tags="era_bar_bg"
        )
        cv.create_rectangle(
            ERA_BAR_X, ERA_BAR_Y, ERA_BAR_X, ERA_BAR_Y + ERA_BAR_H,
            fill=COLOR_ERA_BAR_FILL, outline="", tags="era_bar_fill"
        )
        cv.create_text(
            ERA_BAR_X + ERA_BAR_W + 10, ERA_BAR_Y + ERA_BAR_H // 2,
            anchor="w", text="", fill=COLOR_ERA_LABEL,
            font=get_font(10, True), tags="era_label"
        )
        cv.create_text(
            ERA_BAR_X + ERA_BAR_W // 2, ERA_BAR_Y + ERA_BAR_H // 2,
            text="", fill=COLOR_ERA_TEXT, font=get_font(9), tags="era_text"
        )

        # 分类标签
        tab_keys = ["all", "click", "dps", "multiplier", "synergy", "utility"]
        self._tab_ids = {}
        for i, cat_key in enumerate(tab_keys):
            ci = CATEGORIES.get(cat_key, {"name": cat_key})
            tx = TABS_X + i * TAB_SPACING
            rect = cv.create_rectangle(
                tx, TABS_Y, tx + TAB_W, TABS_Y + TAB_H,
                fill=COLOR_TAB_INACTIVE, outline="",
                tags=(f"tab_{cat_key}", "tabs")
            )
            txt = cv.create_text(
                tx + TAB_W // 2, TABS_Y + TAB_H // 2,
                text=ci["name"], fill=COLOR_TAB_TEXT,
                font=get_font(9), tags=(f"tab_{cat_key}", "tabs")
            )
            self._tab_ids[cat_key] = (rect, txt)
            cv.tag_bind(f"tab_{cat_key}", "<Button-1>",
                        lambda e, k=cat_key: self._set_category(k))
        self._highlight_active_tab()

    def update_era_bar(self, engine):
        era = engine.get_current_era()
        nxt = engine.get_next_era()
        p = engine.get_era_progress()
        w = int(ERA_BAR_W * p)
        self.top_cv.coords("era_bar_fill", ERA_BAR_X, ERA_BAR_Y, ERA_BAR_X + w, ERA_BAR_Y + ERA_BAR_H)
        if nxt:
            self.top_cv.itemconfig("era_label", text=f"{era['name']} → {nxt['name']}")
            self.top_cv.itemconfig("era_text", text=f"{p*100:.0f}%")
        else:
            self.top_cv.itemconfig("era_label", text=f"{era['name']} (最高)")
            self.top_cv.itemconfig("era_text", text="满级")

    def _set_category(self, cat_key: str):
        self._active_category = cat_key
        self._highlight_active_tab()

    def _highlight_active_tab(self):
        for cat_key, (rect, txt) in self._tab_ids.items():
            a = (cat_key == self._active_category)
            self.top_cv.itemconfig(rect, fill=COLOR_TAB_ACTIVE if a else COLOR_TAB_INACTIVE)
            self.top_cv.itemconfig(txt, fill="white" if a else COLOR_TAB_TEXT)

    # =========================== 右面板绘制 ===========================

    def _draw_panel_static(self):
        cv = self.panel_cv

        # Hero
        r = HERO_R
        cv.create_oval(
            HERO_CX - r, HERO_CY - r, HERO_CX + r, HERO_CY + r,
            fill=COLOR_HERO, outline="", tag="hero"
        )
        cv.create_text(HERO_CX, HERO_CY, text="英雄", fill="white",
                       font=get_font(14, True), tag="hero")
        cv.tag_bind("hero", "<Button-1>", self._on_click)
        cv.create_text(HERO_CX, HERO_CY + r + 12, text="",
                       fill=COLOR_GOLDEN_BTN, font=get_font(9, True),
                       tags="golden_timer")

        # 技能按钮（grid 布局）
        self._skill_btn_ids: dict = {}
        for i, sk in enumerate(SKILLS):
            col = i % SKILL_COLS
            row = i // SKILL_COLS
            sx = SKILL_X + col * (SKILL_W + SKILL_GAP_X)
            sy = SKILL_Y + row * (SKILL_H + SKILL_GAP_Y)
            rect = cv.create_rectangle(
                sx, sy, sx + SKILL_W, sy + SKILL_H,
                fill=COLOR_SKILL_COOLDOWN, outline="#555", width=1,
                tags=(f"skill_{sk['key']}", "skills")
            )
            txt = cv.create_text(
                sx + SKILL_W // 2, sy + SKILL_H // 2,
                text=f"{sk['icon']} {sk['name']}", fill="#888",
                font=get_font(8), tags=(f"skill_{sk['key']}", "skills")
            )
            self._skill_btn_ids[sk["key"]] = (rect, txt)
            cv.tag_bind(f"skill_{sk['key']}", "<Button-1>",
                        lambda e, k=sk["key"]: self._on_skill(k))

        # 英雄面板
        self._hero_btn_ids: dict = {}
        for i, h in enumerate(HEROES):
            hy = HERO_PANEL_Y + i * HERO_PANEL_SPACING
            rect = cv.create_rectangle(
                HERO_PANEL_X, hy,
                HERO_PANEL_X + HERO_PANEL_W, hy + HERO_PANEL_H,
                fill="#1a1a3e", outline="#444", width=1,
                tags=(f"hero_{h['key']}", "hero_btns")
            )
            txt = cv.create_text(
                HERO_PANEL_X + 8, hy + HERO_PANEL_H // 2, anchor="w",
                text=f"{h['icon']} {h['name']}", fill="#666",
                font=get_font(9), tags=(f"hero_{h['key']}", "hero_btns")
            )
            self._hero_btn_ids[h["key"]] = (rect, txt, hy)
            cv.tag_bind(f"hero_{h['key']}", "<Button-1>",
                        lambda e, k=h["key"]: self._on_hero("upgrade", k))

        # 转生按钮
        cv.create_rectangle(
            PRESTIGE_X, PRESTIGE_Y,
            PRESTIGE_X + PRESTIGE_W, PRESTIGE_Y + PRESTIGE_H,
            fill=COLOR_PRESTIGE_BTN, outline="#fff", width=1,
            tags=("prestige_btn",)
        )
        cv.create_text(
            PRESTIGE_X + PRESTIGE_W // 2, PRESTIGE_Y + PRESTIGE_H // 2,
            text="转生", fill="#000", font=get_font(10, True),
            tags=("prestige_btn",)
        )
        cv.tag_bind("prestige_btn", "<Button-1>", lambda e: self._on_prestige())

    # =========================== 底栏绘制 ===========================

    def _draw_bottom_static(self):
        cv = self.bottom_cv
        cv.create_text(10, EQUIP_PANEL_Y + 2, anchor="w",
                       text="🎒", fill="#888", font=get_font(10),
                       tags="equip_label")
        self._equip_tids: list = []
        self._prestige_status_tid: int = 0

    # =========================== 面板刷新 ===========================

    def update_skill_buttons(self, engine):
        cv = self.panel_cv
        for key, (rect, txt) in self._skill_btn_ids.items():
            cd = engine.get_skill_cooldown(key)
            ar = engine.get_skill_active_remaining(key)
            sk = engine.get_skill_info(key)
            era_ok = engine.is_era_unlocked(sk["era"]) if sk else False
            if not era_ok:
                c, l, tc = COLOR_LOCKED, f"🔒 {sk['name']}", COLOR_LOCKED_TEXT
            elif ar > 0:
                c, l, tc = COLOR_SKILL_ACTIVE, f"{sk['icon']} {int(ar)}s", "white"
            elif cd > 0:
                c, l, tc = COLOR_SKILL_COOLDOWN, f"{sk['icon']} {int(cd)}s", "#888"
            else:
                c, l, tc = COLOR_SKILL_READY, f"{sk['icon']} {sk['name']}", "white"
            cv.itemconfig(rect, fill=c)
            cv.itemconfig(txt, text=l, fill=tc)

    def update_hero_panel(self, engine):
        cv = self.panel_cv
        for key, (rect, txt, hy) in self._hero_btn_ids.items():
            hdef = engine.get_hero_info(key)
            hstate = engine.get_hero_state(key)
            lv = hstate["level"]
            if lv <= 0:
                cost = hdef["unlock_gold"]
                label = f"{hdef['icon']} {hdef['name']}  招募 {self._fmt_gold(cost)}"
                cf, ct = "#1a1a3e", "#888"
            else:
                cost = engine.get_hero_upgrade_cost(key)
                if lv >= hdef["max_level"]:
                    label = f"{hdef['icon']} {hdef['name']}  {lv}级 满级"
                    cf, ct = "#1a1a3e", "#ffd369"
                else:
                    label = f"{hdef['icon']} {hdef['name']}  {lv}级 → {self._fmt_gold(cost)}"
                    can = engine.state.gold >= cost
                    cf = COLOR_BTN_BG if can else "#1a1a3e"
                    ct = COLOR_BTN_TEXT if can else "#888"
            cv.itemconfig(rect, fill=cf)
            cv.itemconfig(txt, text=label, fill=ct)

    def update_golden_timer(self, remaining: float, active: bool):
        t = f"增益: {remaining:.0f}s" if active else ""
        self.panel_cv.itemconfig("golden_timer", text=t)

    # =========================== 装备底栏 ===========================

    def update_equipment_bar(self, engine):
        cv = self.bottom_cv
        for tid in self._equip_tids:
            cv.delete(tid)
        self._equip_tids = []

        eqs = engine.get_equipment()
        show = eqs[-EQUIP_MAX_SHOW:] if len(eqs) > EQUIP_MAX_SHOW else eqs
        for i, eq in enumerate(show):
            ex = 30 + i * (EQUIP_ITEM_W + EQUIP_SPACING)
            tid = cv.create_text(
                ex, EQUIP_PANEL_Y + 2, anchor="w",
                text=f"{eq['name']} +{eq['bonus']}",
                fill=eq["color"], font=get_font(8)
            )
            self._equip_tids.append(tid)

        pts = engine.state.prestige_points
        ch = engine.get_active_challenge()
        status = ""
        if ch:
            status = f"  |  {ch['name']}"
            if ch.get("time_limit"):
                status += f" {max(0,int(ch['time_limit']-(time.time()-engine.state.challenge_start_time)))}s"
        cv.delete("prestige_bottom")
        cv.create_text(
            WINDOW_WIDTH - 10, EQUIP_PANEL_Y + 2, anchor="e",
            text=f"声望: {pts}{status}", fill=COLOR_PRESTIGE_BTN,
            font=get_font(9, True), tags="prestige_bottom"
        )

    # =========================== HUD ===========================

    def draw_hud(self, gold: float, dps: float):
        cv = self.top_cv
        cv.create_text(HUD_X, HUD_Y_GOLD, anchor="nw",
                       text=f"金币：{self._fmt_gold(gold)}",
                       fill=COLOR_GOLD, font=get_font(13, True), tags="hud_gold")
        cv.create_text(HUD_X, HUD_Y_DPS, anchor="nw",
                       text=f"产出：{self._fmt_dps(dps)}/s",
                       fill=COLOR_DPS, font=get_font(10), tags="hud_dps")

    def refresh_hud(self, gold: float, dps: float):
        self.top_cv.itemconfig("hud_gold", text=f"金币：{self._fmt_gold(gold)}")
        self.top_cv.itemconfig("hud_dps", text=f"产出：{self._fmt_dps(dps)}/s")

    # =========================== 商店 ===========================

    def draw_shop_buttons(self, engine):
        self._clear_shop()
        visible = engine.get_visible_upgrades(self._active_category)
        self._visible_keys = {d.key for d in visible}
        h = max(len(visible) * SHOP_SPACING + SHOP_SCROLL_PADDING, 10)
        self.shop_cv.config(scrollregion=(0, 0, SHOP_W + SHOP_SCROLL_PADDING, h))
        for i, d in enumerate(visible):
            y = SHOP_Y0 + i * SHOP_SPACING
            qty = engine.state.upgrades.get(d.key, 0)
            cost = d.get_cost(qty)
            af = engine.state.gold >= cost
            ok = engine.check_prerequisite(d) and engine.is_era_unlocked(d.era)
            self._draw_one_btn(d.key, d, qty, cost, af, ok, y)

    def _draw_one_btn(self, key, d, qty, cost, af, ok, y):
        ci = CATEGORIES.get(d.category, {})
        cc = ci.get("color", COLOR_BTN_OUT)
        if not ok:
            fb, ft, oc = COLOR_LOCKED, COLOR_LOCKED_TEXT, "#444"
        elif af:
            fb, ft, oc = COLOR_BTN_BG, COLOR_BTN_TEXT, cc
        else:
            fb, ft, oc = "#2a2a3e", "#666", "#444"

        rect = self.shop_cv.create_rectangle(
            SHOP_X, y, SHOP_X + SHOP_W, y + SHOP_H,
            fill=fb, outline=oc, width=1,
            tags=(f"btn_{key}", "shop_btn")
        )
        label = self._make_btn_label(d, qty, cost)
        if not ok:
            label += f" [{d.era}]"
        txt = self.shop_cv.create_text(
            SHOP_X + SHOP_W // 2, y + SHOP_H // 2,
            text=label, fill=ft, font=get_font(9),
            tags=(f"txt_{key}", "shop_btn")
        )
        self.shop_cv.create_rectangle(
            SHOP_X, y, SHOP_X + 4, y + SHOP_H,
            fill=cc, outline="", tags="shop_btn"
        )
        self._btn_items[key] = (rect, txt)
        cb = lambda e, k=key: self._on_buy(k)
        self.shop_cv.tag_bind(f"btn_{key}", "<Button-1>", cb)
        self.shop_cv.tag_bind(f"txt_{key}", "<Button-1>", cb)

    def refresh_shop_buttons(self, engine):
        for key, (rect, txt) in list(self._btn_items.items()):
            d = engine.get_def(key)
            if d is None:
                continue
            qty = engine.state.upgrades.get(key, 0)
            cost = d.get_cost(qty)
            af = engine.state.gold >= cost
            ok = engine.check_prerequisite(d) and engine.is_era_unlocked(d.era)
            fb = COLOR_LOCKED if not ok else (COLOR_BTN_BG if af else "#2a2a3e")
            ft = COLOR_LOCKED_TEXT if not ok else (COLOR_BTN_TEXT if af else "#666")
            self.shop_cv.itemconfig(rect, fill=fb)
            label = self._make_btn_label(d, qty, cost)
            if not ok:
                label += f" [{d.era}]"
            self.shop_cv.itemconfig(txt, text=label, fill=ft)

    def refresh_shop_if_needed(self, engine):
        v = {d.key for d in engine.get_visible_upgrades(self._active_category)}
        if v != self._visible_keys:
            self.draw_shop_buttons(engine)

    # =========================== 浮动飘字 ===========================

    def spawn_float(self, text: str):
        x = FLOAT_BASE_X + random.randint(-FLOAT_OFFSET_RANGE, FLOAT_OFFSET_RANGE)
        tid = self.panel_cv.create_text(
            x, FLOAT_BASE_Y, text=text,
            fill=COLOR_FLOAT, font=get_font(11, True)
        )
        self.floaters.append([tid, 0.0, FLOAT_BASE_Y])

    def update_floaters(self, dt: float):
        for f in self.floaters[:]:
            f[1] += dt
            tid, age, by = f
            if age > FLOAT_LIFETIME:
                self.panel_cv.delete(tid)
                self.floaters.remove(f)
            else:
                self.panel_cv.coords(tid, self.panel_cv.coords(tid)[0], by - FLOAT_SPEED * age)

    # =========================== 对话框 ===========================

    def show_prestige_dialog(self, engine):
        return messagebox.askyesno("转生",
            f"重置进度，获得 {engine.get_prestige_formula()} 声望。确定？")

    def show_challenge_dialog(self, engine) -> str | None:
        chs = engine.get_challenges()
        lines = [f"{i+1}. {c['name']} (x{c.get('prestige_mult',1):.1f}) — {c['tip']}"
                 for i, c in enumerate(chs)]
        r = simpledialog.askstring("挑战",
            "\n".join(lines) + f"\n\n编号 (1-{len(chs)})：")
        if r and r.isdigit():
            i = int(r) - 1
            if 0 <= i < len(chs):
                return chs[i]["key"]
        return None

    def show_prestige_shop(self, engine):
        pus = engine.get_prestige_upgrades()
        lines = [f"  {p['name']}: {engine.state.prestige_upgrades.get(p['key'],0)}级/"
                 f"{p['max_level']} ({p['cost']}声望/级)" for p in pus]
        messagebox.showinfo("声望商店",
            f"声望: {engine.state.prestige_points}\n\n" + "\n".join(lines))

    # =========================== 内部 ===========================

    def _clear_shop(self):
        self.shop_cv.delete("shop_btn")
        self._btn_items.clear()
        self._visible_keys.clear()

    def _make_btn_label(self, d, qty, cost):
        l = d.description_tpl.replace("{cost}", self._fmt_gold(cost))
        l = l.replace("{qty}", str(qty))
        if d.per_second > 0:
            l += f" (+{self._fmt_dps(d.per_second)}/s)"
        return l

    def _on_mousewheel(self, event):
        self.shop_cv.yview_scroll(-1 * (event.delta // 120), "units")

    @staticmethod
    def _fmt_gold(v):
        return f"{int(v):,}" if v < 1e15 else GameUI._fmt_big(v)

    @staticmethod
    def _fmt_dps(v):
        return GameUI._fmt_big(v)

    @staticmethod
    def _fmt_big(v):
        if v < 1e15: return f"{int(v):,}"
        if v < 1e308: return f"{v:.1e}"
        q = 0
        while v > 1e308: q += 1; v //= 1e308
        b, s = f"{v:.1e}".split("e+")
        return f"{b}e+{GameUI._fmt_big(int(s)+308*q)}"
