"""
action_dispatcher.py — Translates a GestureState into real OS actions
(mouse move, click, scroll, screenshot, volume) via PyAutoGUI / platform
system calls.

Design goals:
  • Smoothing     – exponential moving average on cursor position
  • Debouncing    – gestures must be held for N frames before firing
  • Cooldown      – after a discrete action, a short cooldown prevents
                    accidental repeat triggers
"""

from __future__ import annotations

import os
import time
import platform
from collections import deque
from typing import Deque, Optional

import pyautogui
import pygetwindow  # type: ignore  (optional, graceful fallback)

from config import Config
from gesture_engine import GestureState

pyautogui.PAUSE    = 0.0
pyautogui.FAILSAFE = True


class Debouncer:
    """True only after the gesture has been held for *threshold* frames."""

    def __init__(self, threshold: int) -> None:
        self._threshold = threshold
        self._counter   = 0
        self._active    = False

    def update(self, held: bool) -> bool:
        if held:
            self._counter += 1
        else:
            self._counter = 0
            self._active  = False

        if self._counter >= self._threshold and not self._active:
            self._active = True
            return True          # rising edge
        return False

    def reset(self) -> None:
        self._counter = 0
        self._active  = False

    @property
    def holding(self) -> bool:
        return self._counter >= self._threshold


class ActionDispatcher:
    """Stateful dispatcher: consumes GestureState, fires OS actions."""

    def __init__(self, config: Config) -> None:
        self.cfg = config

        # Smoothed cursor position in *screen* pixels
        self._sx: float = config.SCREEN_W / 2
        self._sy: float = config.SCREEN_H / 2

        # Debounced gesture detectors
        self._db_lclick = Debouncer(config.CLICK_DEBOUNCE_FRAMES)
        self._db_rclick = Debouncer(config.CLICK_DEBOUNCE_FRAMES)
        self._db_scroll  = Debouncer(config.SCROLL_DEBOUNCE_FRAMES)
        self._db_shot    = Debouncer(config.SCREENSHOT_DEBOUNCE_FRAMES)
        self._db_toggle  = Debouncer(config.TOGGLE_DEBOUNCE_FRAMES)

        # State
        self.control_enabled: bool = True
        self._last_screenshot: float = 0.0
        self._screenshot_count: int  = 0

        # Stats for HUD
        self.last_action: str  = "–"
        self.action_time: float = 0.0

    # ── Public ──────────────────────────────────────────────────

    def dispatch(self, state: GestureState) -> None:
        """Call once per frame with the latest GestureState."""

        # ── Toggle mode (always active) ─────────────────────────
        if self._db_toggle.update(state.toggle):
            self.control_enabled = not self.control_enabled
            self.last_action = (
                "Control ON" if self.control_enabled else "Control OFF"
            )
            self.action_time = time.time()

        if not self.control_enabled or not state.hand_detected:
            # Reset click debouncers so no phantom click fires on resume
            self._db_lclick.reset()
            self._db_rclick.reset()
            return

        # ── Cursor movement ─────────────────────────────────────
        target_x = state.cursor_norm[0] * self.cfg.SCREEN_W
        target_y = state.cursor_norm[1] * self.cfg.SCREEN_H
        self._sx, self._sy = self._smooth(target_x, target_y)
        pyautogui.moveTo(self._sx, self._sy)

        # ── Left click ──────────────────────────────────────────
        if self._db_lclick.update(state.left_click):
            pyautogui.click()
            self._set_action("Left click")
        self._db_rclick.update(not state.left_click and state.right_click)

        # ── Right click ─────────────────────────────────────────
        if self._db_rclick.update(state.right_click):
            pyautogui.rightClick()
            self._set_action("Right click")
        self._db_lclick.update(not state.right_click and state.left_click)

        # ── Scroll ──────────────────────────────────────────────
        if state.scroll_ticks != 0:
            if self._db_scroll.update(True):
                pyautogui.scroll(state.scroll_ticks)
                direction = "↑" if state.scroll_ticks > 0 else "↓"
                self._set_action(f"Scroll {direction}")
        else:
            self._db_scroll.update(False)

        # ── Screenshot ──────────────────────────────────────────
        now = time.time()
        if self._db_shot.update(state.screenshot):
            if now - self._last_screenshot > 2.0:   # 2 s cooldown
                self._take_screenshot()
                self._last_screenshot = now

        # ── Volume (platform-specific, best-effort) ─────────────
        # (Volume gestures are not wired in the default gesture set
        #  but you can hook them here.)

    # ── Internals ───────────────────────────────────────────────

    def _smooth(self, tx: float, ty: float):
        a = self.cfg.SMOOTHING_ALPHA
        sx = a * tx + (1 - a) * self._sx
        sy = a * ty + (1 - a) * self._sy
        return sx, sy

    def _set_action(self, label: str) -> None:
        self.last_action = label
        self.action_time = time.time()

    def _take_screenshot(self) -> None:
        self._screenshot_count += 1
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"screenshot_{ts}_{self._screenshot_count}.png"
        img = pyautogui.screenshot()
        img.save(filename)
        self._set_action(f"Screenshot → {filename}")
        print(f"[INFO] Screenshot saved: {filename}")
