"""
黄金按钮 Mixin — 黄金 buff 激活、调度、属性查询。
"""
import random
from config import GOLDEN_BUFF


class _GoldenMixin:
    """提供给 GameEngine 的黄金按钮相关方法。"""

    _golden_buff_active: bool
    _golden_buff_remaining: float
    _golden_button_visible: bool
    _golden_button_timer: float

    def _activate_golden(self):
        self._golden_buff_active = True
        self._golden_buff_remaining = GOLDEN_BUFF["duration"]
        self._golden_button_visible = False
        self._schedule_golden_button()

    def _schedule_golden_button(self):
        delay = random.randint(GOLDEN_BUFF["button_delay_min"], GOLDEN_BUFF["button_delay_max"])
        self._golden_button_timer = delay

    def golden_button_clicked(self):
        self._activate_golden()
        self._recalc()

    @property
    def golden_buff_active(self) -> bool:
        return self._golden_buff_active

    @property
    def golden_button_visible(self) -> bool:
        return self._golden_button_visible

    @property
    def golden_buff_remaining(self) -> float:
        return self._golden_buff_remaining
