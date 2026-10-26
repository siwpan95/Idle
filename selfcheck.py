#!/usr/bin/env python3
"""Headless self-check for Idle (no tkinter, no window).

Exercises the pure game engine only:

* number formatting for small / scientific / huge integers,
* click income and statistics,
* single and batch purchases (gold, level, DPS),
* per-tick production and play-time advance,
* save export/import (base64) round-trip.

Run from the project root:

    python selfcheck.py

Prints ``selfcheck ok: ...`` and returns 0 on success, ``FAIL: ...`` and 1
on failure.  No project file is written (the temporary save lives in memory).
"""
from __future__ import annotations

from engine import GameEngine, fmt_num
from engine.state import GameState

CHECKS: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    """Record one functional check; abort on mismatch."""
    if not condition:
        raise AssertionError(f"{name}: {detail or 'condition is false'}")
    CHECKS.append(name)


def fresh_engine() -> GameEngine:
    """A deterministic new-game engine, independent of any idle_save.json."""
    eng = GameEngine()
    eng.state = GameState()
    eng._era_index = 0
    eng._init_state()
    eng._update_era()
    eng._recalc()
    return eng


def check_formatting() -> None:
    check("fmt.small", fmt_num(0) == "0", repr(fmt_num(0)))
    check("fmt.thousands", fmt_num(1234) == "1,234", repr(fmt_num(1234)))
    check("fmt.scientific", fmt_num(10 ** 15) == "1.00e15", repr(fmt_num(10 ** 15)))
    check("fmt.bigint", fmt_num(10 ** 30) == "1.00e30", repr(fmt_num(10 ** 30)))
    check("fmt.hugeint", fmt_num(10 ** 400) == "1.00e400", repr(fmt_num(10 ** 400)))
    check("fmt.infinity", fmt_num(float("inf")) == "\u221e", repr(fmt_num(float("inf"))))
    check("fmt.negative", fmt_num(-42) == "-42", repr(fmt_num(-42)))


def check_click_and_buy() -> GameEngine:
    eng = fresh_engine()

    click_power = eng.state.click_power
    gold_before = eng.state.gold
    gain = eng.click()
    check("click.gain", abs(gain - click_power) < 1e-9, f"{gain} != {click_power}")
    check("click.gold", abs(eng.state.gold - gold_before - gain) < 1e-9)
    check("click.stats", eng.state.stats["clicks"] == 1, eng.state.stats)

    eng.state.gold = 10 ** 6
    cost = eng.get_cost("noob_clicker")
    qty, err = eng.buy_multiple("noob_clicker", 1)
    check("buy.ok", qty == 1 and err is None, f"qty={qty} err={err!r}")
    check("buy.level", eng.state.upgrades["noob_clicker"] == 1)
    spent = 10 ** 6 - eng.state.gold
    check("buy.cost", abs(spent - cost) < 1e-9, f"spent={spent} cost={cost}")
    dps_one = eng.state.dps
    check("buy.dps", dps_one > 0, dps_one)

    qty2, err2 = eng.buy_multiple("noob_clicker", "max")
    check("buy.batch", qty2 > 0 and err2 is None, f"qty={qty2} err={err2!r}")
    check("buy.dps_grows", eng.state.dps > dps_one, f"{dps_one} -> {eng.state.dps}")
    return eng


def check_tick(eng: GameEngine) -> None:
    dps = eng.state.dps
    gold_before = eng.state.gold
    play_before = eng.state.play_time
    dt = eng.tick(eng.state.last_tick + 0.5)
    check("tick.dt", abs(dt - 0.5) < 1e-9, dt)
    check("tick.gold", abs((eng.state.gold - gold_before) - dps * dt) < 1e-6,
          f"delta={eng.state.gold - gold_before} expected={dps * dt}")
    check("tick.play_time", abs((eng.state.play_time - play_before) - dt) < 1e-9)


def check_save_roundtrip(eng: GameEngine) -> None:
    eng.state.gold = 4242.5
    blob = eng.export_save()
    check("save.export", isinstance(blob, str) and len(blob) > 100, len(blob))

    restored = GameEngine()
    restored.state = GameState()
    restored._init_state()
    restored.import_save(blob)
    check("save.gold", abs(restored.state.gold - 4242.5) < 1e-9, restored.state.gold)
    check("save.level",
          restored.state.upgrades.get("noob_clicker") == eng.state.upgrades["noob_clicker"],
          restored.state.upgrades.get("noob_clicker"))
    check("save.upgrades", restored.state.upgrades == eng.state.upgrades)
    check("save.stats",
          restored.state.stats.get("clicks") == eng.state.stats.get("clicks"),
          f"{restored.state.stats} != {eng.state.stats}")


def run() -> None:
    check_formatting()
    eng = check_click_and_buy()
    check_tick(eng)
    check_save_roundtrip(eng)


def main() -> int:
    try:
        run()
    except Exception as exc:  # noqa: BLE001 - self-check must report, not traceback
        print(f"FAIL: {type(exc).__name__}: {exc}")
        return 1
    print(f"selfcheck ok: idle engine ({len(CHECKS)} checks: format/click/buy/tick/save)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
