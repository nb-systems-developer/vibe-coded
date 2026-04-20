"""
config.py — All tuneable parameters in one place.
Change values here to calibrate for your screen / environment.
"""

import pyautogui
import screeninfo


class Config:
    # ── Camera ──────────────────────────────────────────────────
    CAMERA_INDEX: int = 0       # Try 1 or 2 if the default doesn't work
    CAP_WIDTH:    int = 640
    CAP_HEIGHT:   int = 480
    CAP_FPS:      int = 30

    # ── Screen (auto-detected, override if needed) ───────────────
    try:
        _m = screeninfo.get_monitors()[0]
        SCREEN_W: int = _m.width
        SCREEN_H: int = _m.height
    except Exception:
        SCREEN_W, SCREEN_H = pyautogui.size()

    # ── Hand tracking zone (fraction of frame used as control area)
    # Helps avoid the cursor getting "stuck" at the very edges.
    CONTROL_MARGIN: float = 0.10   # 10 % margin on each side

    # ── Cursor smoothing (exponential moving average) ───────────
    # 0.0 = no movement, 1.0 = raw (jittery). ~0.15–0.25 works well.
    SMOOTHING_ALPHA: float = 0.20

    # ── Gesture thresholds (fractions of hand-width) ─────────────
    PINCH_THRESHOLD:  float = 0.055   # Index + thumb → left click
    RCLICK_THRESHOLD: float = 0.060   # Middle + thumb → right click

    # ── Gesture debounce (frames a gesture must persist) ─────────
    CLICK_DEBOUNCE_FRAMES:      int = 6
    SCROLL_DEBOUNCE_FRAMES:     int = 3
    SCREENSHOT_DEBOUNCE_FRAMES: int = 20
    TOGGLE_DEBOUNCE_FRAMES:     int = 20

    # ── Scroll sensitivity ───────────────────────────────────────
    SCROLL_SENSITIVITY: float = 8.0   # Pixels of finger movement → 1 scroll tick

    # ── MediaPipe ───────────────────────────────────────────────
    MAX_HANDS:          int   = 2
    DETECTION_CONF:     float = 0.75
    TRACKING_CONF:      float = 0.65

    # ── Display ─────────────────────────────────────────────────
    DISPLAY_W: int = 900    # Width of the HUD window (frame is scaled to this)
    LANDMARK_COLOR   = (0,   255, 180)
    CONNECTION_COLOR = (255, 255, 255)
    HUD_BG_COLOR     = (10,  10,  10)

    # ── PyAutoGUI safety ────────────────────────────────────────
    PYAUTOGUI_PAUSE:    float = 0.0    # No artificial delay
    PYAUTOGUI_FAILSAFE: bool  = True   # Move mouse to corner to abort
