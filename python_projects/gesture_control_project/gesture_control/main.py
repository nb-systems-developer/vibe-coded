"""
╔══════════════════════════════════════════════════════════════╗
║           HAND GESTURE COMPUTER CONTROL SYSTEM               ║
║                     main.py                                  ║
╚══════════════════════════════════════════════════════════════╝

Entry point — initialises the camera, gesture engine, and
action dispatcher, then runs the main event loop.
"""

import sys
import cv2
from gesture_engine import GestureEngine
from action_dispatcher import ActionDispatcher
from overlay import Overlay
from config import Config


def main() -> None:
    config = Config()

    # ── Camera Setup ────────────────────────────────────────────
    cap = cv2.VideoCapture(config.CAMERA_INDEX)
    if not cap.isOpened():
        print(
            f"[ERROR] Cannot open camera at index {config.CAMERA_INDEX}.\n"
            "  • Make sure your webcam is connected.\n"
            "  • Try changing CAMERA_INDEX in config.py (e.g. 1 or 2)."
        )
        sys.exit(1)

    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  config.CAP_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAP_HEIGHT)
    cap.set(cv2.CAP_PROP_FPS,          config.CAP_FPS)

    print(
        "\n══════════════════════════════════════════\n"
        "   Hand Gesture Computer Control — READY  \n"
        "══════════════════════════════════════════\n"
        "  Index tip         → Move cursor\n"
        "  Thumb + Index     → Left click\n"
        "  Thumb + Middle    → Right click\n"
        "  Index + Middle ↑↓ → Scroll\n"
        "  Ring finger up    → Screenshot\n"
        "  Pinky up          → Toggle control\n"
        "  Press  Q          → Quit\n"
        "══════════════════════════════════════════\n"
    )

    engine     = GestureEngine(config)
    dispatcher = ActionDispatcher(config)
    overlay    = Overlay(config)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("[WARN] Dropped frame — retrying…")
                continue

            # Mirror so it feels natural
            frame = cv2.flip(frame, 1)

            # Detect gestures and get annotated frame + state
            gesture_state, annotated_frame = engine.process(frame)

            # Execute mouse / keyboard actions
            dispatcher.dispatch(gesture_state)

            # Draw HUD overlay
            display_frame = overlay.draw(annotated_frame, gesture_state, dispatcher)

            cv2.imshow("Gesture Control  |  press Q to quit", display_frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                print("[INFO] Q pressed — exiting.")
                break

    except KeyboardInterrupt:
        print("\n[INFO] Interrupted — exiting.")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        engine.close()


if __name__ == "__main__":
    main()
