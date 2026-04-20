"""
gesture_engine.py — Wraps MediaPipe Hands and converts raw
landmark data into a high-level GestureState dataclass.

Key design decisions:
  • We work with *normalised* landmark coords (0–1) throughout so
    the logic is resolution-independent.
  • Distances are divided by the hand's "reference width" (wrist→
    middle-MCP) so that pinch thresholds work at any hand depth.
  • Only the hand with the highest confidence (or the first
    detected) is used for control; a second hand is ignored.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple, List

import cv2
import mediapipe as mp
import numpy as np

from config import Config


# ── Landmark indices (MediaPipe convention) ──────────────────────
WRIST          = 0
THUMB_TIP      = 4
INDEX_MCP      = 5
INDEX_TIP      = 8
MIDDLE_MCP     = 9
MIDDLE_TIP     = 12
RING_TIP       = 16
PINKY_TIP      = 20
INDEX_PIP      = 6
MIDDLE_PIP     = 10
RING_PIP       = 14
PINKY_PIP      = 18


@dataclass
class GestureState:
    """All the information the ActionDispatcher needs each frame."""
    # Cursor position (normalised 0–1, within control zone)
    cursor_norm: Tuple[float, float] = (0.5, 0.5)

    # Active gestures (True = gesture held this frame)
    left_click:  bool = False
    right_click: bool = False
    scroll_up:   bool = False
    scroll_down: bool = False
    screenshot:  bool = False
    toggle:      bool = False      # Pinky raised → toggle control on/off

    # Scroll magnitude (scroll ticks requested this frame)
    scroll_ticks: int = 0

    # Debugging info shown on HUD
    gesture_label: str  = "–"
    hand_detected: bool = False
    fps:           float = 0.0

    # Raw finger-up flags (used internally by overlay)
    fingers_up: List[bool] = field(default_factory=lambda: [False]*5)


class GestureEngine:
    """Processes a BGR frame and returns (GestureState, annotated_frame)."""

    def __init__(self, config: Config) -> None:
        self.cfg = config

        self._mp_hands = mp.solutions.hands
        self._mp_draw  = mp.solutions.drawing_utils
        self._mp_style = mp.solutions.drawing_styles

        self._hands = self._mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=config.MAX_HANDS,
            min_detection_confidence=config.DETECTION_CONF,
            min_tracking_confidence=config.TRACKING_CONF,
        )

        # Scroll tracking state
        self._prev_scroll_y: Optional[float] = None
        self._scroll_accum:  float = 0.0

        # FPS counter
        self._tick = cv2.getTickCount()

    # ── Public API ───────────────────────────────────────────────

    def process(
        self, frame: np.ndarray
    ) -> Tuple[GestureState, np.ndarray]:
        """Main entry: analyse *frame* and return state + annotated copy."""
        annotated = frame.copy()
        state     = GestureState()
        state.fps = self._calc_fps()

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        results = self._hands.process(rgb)
        rgb.flags.writeable = True

        if not results.multi_hand_landmarks:
            self._prev_scroll_y = None
            return state, annotated

        state.hand_detected = True

        # Pick the first (highest-confidence) hand
        lm_list = results.multi_hand_landmarks[0]
        hand_label = (
            results.multi_handedness[0].classification[0].label
            if results.multi_handedness else "Right"
        )

        # Draw landmarks on annotated frame
        self._draw_landmarks(annotated, lm_list)

        # Convert to pixel coords for easier maths
        h, w = frame.shape[:2]
        pts = self._landmarks_to_array(lm_list, w, h)

        # Reference length = wrist → middle MCP (normalised to frame diag)
        ref = self._dist(pts[WRIST], pts[MIDDLE_MCP]) / math.hypot(w, h) + 1e-6

        # ── Finger states ────────────────────────────────────────
        fingers_up = self._fingers_up(pts, hand_label)
        state.fingers_up = fingers_up
        thumb_up, index_up, middle_up, ring_up, pinky_up = fingers_up

        # ── Cursor position ──────────────────────────────────────
        # Use index fingertip, remapped from the control zone
        ix_n, iy_n = self._to_norm(pts[INDEX_TIP], w, h)
        state.cursor_norm = self._remap_to_control(ix_n, iy_n)

        # ── Pinch distances ──────────────────────────────────────
        d_thumb_index  = self._dist(pts[THUMB_TIP], pts[INDEX_TIP])  / (math.hypot(w,h) * ref)
        d_thumb_middle = self._dist(pts[THUMB_TIP], pts[MIDDLE_TIP]) / (math.hypot(w,h) * ref)

        # ── Gesture detection ────────────────────────────────────
        if pinky_up and not (index_up or middle_up or ring_up):
            state.toggle = True
            state.gesture_label = "Toggle"

        elif ring_up and not (index_up or middle_up or pinky_up):
            state.screenshot = True
            state.gesture_label = "Screenshot"

        elif d_thumb_index < self.cfg.PINCH_THRESHOLD:
            state.left_click = True
            state.gesture_label = "Left Click"

        elif d_thumb_middle < self.cfg.RCLICK_THRESHOLD:
            state.right_click = True
            state.gesture_label = "Right Click"

        elif index_up and middle_up and not thumb_up:
            # Two-finger scroll
            mid_y = (pts[INDEX_TIP][1] + pts[MIDDLE_TIP][1]) / 2
            mid_y_n = mid_y / h

            if self._prev_scroll_y is not None:
                delta = self._prev_scroll_y - mid_y_n   # positive = hand moved up
                self._scroll_accum += delta * self.cfg.SCREEN_H

                ticks = int(self._scroll_accum / self.cfg.SCROLL_SENSITIVITY)
                if ticks != 0:
                    state.scroll_ticks = ticks
                    state.scroll_up    = ticks > 0
                    state.scroll_down  = ticks < 0
                    self._scroll_accum -= ticks * self.cfg.SCROLL_SENSITIVITY
                    state.gesture_label = "Scroll ↑" if ticks > 0 else "Scroll ↓"
                else:
                    state.gesture_label = "Scroll"

            self._prev_scroll_y = mid_y_n

        else:
            self._prev_scroll_y = None
            state.gesture_label = "Move" if index_up else "–"

        return state, annotated

    def close(self) -> None:
        self._hands.close()

    # ── Helpers ──────────────────────────────────────────────────

    def _landmarks_to_array(
        self, lm_list, w: int, h: int
    ) -> List[Tuple[float, float]]:
        return [(lm.x * w, lm.y * h) for lm in lm_list.landmark]

    @staticmethod
    def _dist(a: Tuple[float, float], b: Tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _to_norm(pt: Tuple[float, float], w: int, h: int):
        return pt[0] / w, pt[1] / h

    def _remap_to_control(self, xn: float, yn: float) -> Tuple[float, float]:
        """Map normalised coords from the usable zone → 0–1."""
        m = self.cfg.CONTROL_MARGIN
        xr = (xn - m) / (1 - 2 * m)
        yr = (yn - m) / (1 - 2 * m)
        return max(0.0, min(1.0, xr)), max(0.0, min(1.0, yr))

    def _fingers_up(
        self, pts: List[Tuple[float, float]], hand_label: str
    ) -> List[bool]:
        """Return [thumb, index, middle, ring, pinky] — True if extended."""
        results = []

        # Thumb: compare tip x vs IP joint x (mirrored for left hand)
        if hand_label == "Right":
            results.append(pts[THUMB_TIP][0] < pts[THUMB_TIP - 1][0])
        else:
            results.append(pts[THUMB_TIP][0] > pts[THUMB_TIP - 1][0])

        # Fingers: tip y above PIP joint y (smaller y = higher on screen)
        for tip, pip in [
            (INDEX_TIP,  INDEX_PIP),
            (MIDDLE_TIP, MIDDLE_PIP),
            (RING_TIP,   RING_PIP),
            (PINKY_TIP,  PINKY_PIP),
        ]:
            results.append(pts[tip][1] < pts[pip][1])

        return results

    def _draw_landmarks(self, frame: np.ndarray, lm_list) -> None:
        self._mp_draw.draw_landmarks(
            frame,
            lm_list,
            self._mp_hands.HAND_CONNECTIONS,
            self._mp_style.get_default_hand_landmarks_style(),
            self._mp_style.get_default_hand_connections_style(),
        )

    def _calc_fps(self) -> float:
        now = cv2.getTickCount()
        fps = cv2.getTickFrequency() / (now - self._tick)
        self._tick = now
        return fps
