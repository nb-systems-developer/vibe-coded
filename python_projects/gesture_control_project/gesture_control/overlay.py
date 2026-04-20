"""
overlay.py — Draws the real-time HUD (heads-up display) on the webcam
feed: gesture label, FPS, control mode, action flash, finger indicators.
"""

from __future__ import annotations

import time
import math
import cv2
import numpy as np

from config import Config
from gesture_engine import GestureState
# Import only the type so we avoid a circular dependency at runtime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from action_dispatcher import ActionDispatcher


# Colour palette
C_GREEN   = (80,  230, 100)
C_RED     = (60,  60,  220)
C_CYAN    = (220, 220,  50)
C_WHITE   = (240, 240, 240)
C_GREY    = (120, 120, 120)
C_AMBER   = (40,  170, 230)
C_BG      = (10,  10,  10)
C_PANEL   = (30,  30,  30)


def _put(
    frame, text, pos, scale=0.55, color=C_WHITE,
    thickness=1, font=cv2.FONT_HERSHEY_DUPLEX
):
    cv2.putText(frame, text, pos, font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(frame, text, pos, font, scale, color,   thickness,     cv2.LINE_AA)


class Overlay:
    def __init__(self, config: Config) -> None:
        self.cfg = config

    def draw(
        self,
        frame: np.ndarray,
        state: GestureState,
        dispatcher: "ActionDispatcher",
    ) -> np.ndarray:
        """Return a new frame with all HUD elements painted on."""

        # Scale to desired display width while keeping aspect ratio
        h, w = frame.shape[:2]
        scale = self.cfg.DISPLAY_W / w
        disp_w = int(w * scale)
        disp_h = int(h * scale)
        frame = cv2.resize(frame, (disp_w, disp_h))

        # Semi-transparent top bar
        self._top_bar(frame, state, dispatcher, disp_w)

        # Finger indicator strip at the bottom
        self._finger_strip(frame, state.fingers_up, disp_w, disp_h)

        # Gesture label pulse
        self._gesture_label(frame, state, disp_w, disp_h)

        # Action flash (bottom-right)
        self._action_flash(frame, dispatcher, disp_w, disp_h)

        # Control-off warning
        if not dispatcher.control_enabled:
            self._disabled_overlay(frame, disp_w, disp_h)

        # Cursor crosshair at mapped position
        if state.hand_detected and dispatcher.control_enabled:
            cx = int(state.cursor_norm[0] * disp_w)
            cy = int(state.cursor_norm[1] * disp_h)
            cv2.circle(frame, (cx, cy), 8,  C_CYAN,  1, cv2.LINE_AA)
            cv2.circle(frame, (cx, cy), 2,  C_CYAN, -1, cv2.LINE_AA)

        return frame

    # ── Helpers ─────────────────────────────────────────────────

    def _top_bar(self, frame, state, dispatcher, w):
        cv2.rectangle(frame, (0, 0), (w, 36), C_PANEL, -1)
        # FPS
        fps_color = C_GREEN if state.fps >= 20 else C_AMBER
        _put(frame, f"FPS {state.fps:4.0f}", (8, 24), color=fps_color, scale=0.5)
        # Screen dims
        _put(
            frame,
            f"Screen {self.cfg.SCREEN_W}×{self.cfg.SCREEN_H}",
            (90, 24), color=C_GREY, scale=0.45,
        )
        # Hand status
        hd_txt   = "Hand ✓" if state.hand_detected else "No hand"
        hd_color = C_GREEN if state.hand_detected else C_RED
        _put(frame, hd_txt, (w // 2 - 40, 24), color=hd_color, scale=0.5)
        # Mode
        mode_txt   = "● ACTIVE" if dispatcher.control_enabled else "○ PAUSED"
        mode_color = C_GREEN if dispatcher.control_enabled else C_RED
        _put(frame, mode_txt, (w - 105, 24), color=mode_color, scale=0.5)

    def _finger_strip(self, frame, fingers_up, w, h):
        labels = ["Thumb", "Index", "Middle", "Ring", "Pinky"]
        n      = len(labels)
        slot_w = w // n
        y_base = h - 10

        cv2.rectangle(frame, (0, h - 34), (w, h), C_PANEL, -1)

        for i, (label, up) in enumerate(zip(labels, fingers_up)):
            cx = slot_w * i + slot_w // 2
            color = C_GREEN if up else C_GREY
            cv2.circle(frame, (cx, y_base - 12), 6, color, -1, cv2.LINE_AA)
            _put(frame, label[0], (cx - 4, y_base), scale=0.38, color=color)

    def _gesture_label(self, frame, state, w, h):
        if not state.hand_detected:
            return
        label = state.gesture_label
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.7, 1)
        x = (w - tw) // 2
        y = h - 50
        # Pill background
        cv2.rectangle(frame, (x - 10, y - th - 6), (x + tw + 10, y + 4), C_PANEL, -1)
        cv2.rectangle(frame, (x - 10, y - th - 6), (x + tw + 10, y + 4), C_CYAN, 1)
        _put(frame, label, (x, y), scale=0.7, color=C_CYAN)

    def _action_flash(self, frame, dispatcher, w, h):
        elapsed = time.time() - dispatcher.action_time
        if elapsed > 1.5:
            return
        alpha = max(0.0, 1.0 - elapsed / 1.5)
        label = dispatcher.last_action
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
        x = w - tw - 14
        y = h - 90
        col = tuple(int(c * alpha) for c in C_AMBER)
        _put(frame, label, (x, y), scale=0.55, color=col)

    def _disabled_overlay(self, frame, w, h):
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (20, 20, 20), -1)
        cv2.addWeighted(overlay, 0.45, frame, 0.55, 0, frame)
        msg = "CONTROL PAUSED  —  raise pinky to resume"
        (tw, _), _ = cv2.getTextSize(msg, cv2.FONT_HERSHEY_DUPLEX, 0.55, 1)
        _put(frame, msg, ((w - tw) // 2, h // 2), scale=0.55, color=C_RED)
