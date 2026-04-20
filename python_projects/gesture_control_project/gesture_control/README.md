# 🖐 Hand Gesture Computer Control

Control your computer with hand gestures captured from a webcam — no special hardware required.

---

## 📁 Project Structure

```
gesture_control/
├── main.py              ← Entry point — run this
├── config.py            ← All tuneable parameters
├── gesture_engine.py    ← MediaPipe hand tracking + gesture recognition
├── action_dispatcher.py ← Converts gestures → OS actions (mouse, click, scroll)
├── overlay.py           ← Real-time HUD drawn on the webcam feed
├── requirements.txt     ← Python dependencies
└── README.md            ← This file
```

---

## ⚙️ Installation

### 1 — Python version

Python **3.9 – 3.11** recommended. MediaPipe has limited support for 3.12+.

```bash
python --version
```

### 2 — Create a virtual environment (strongly recommended)

```bash
python -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### 3 — Install dependencies

```bash
pip install -r requirements.txt
```

> **Linux note:** PyAutoGUI needs `xdotool` for mouse control.
> ```bash
> sudo apt-get install xdotool scrot python3-tk python3-dev
> ```

> **macOS note:** Grant Terminal (or your IDE) permission in
> *System Settings → Privacy & Security → Accessibility* and
> *Screen Recording*.

> **Windows note:** No extra steps required.

---

## ▶️ Running the Application

```bash
python main.py
```

A window labelled **"Gesture Control | press Q to quit"** opens showing your webcam feed.

---

## 🖐 Gesture Reference

| Gesture | Action |
|---------|--------|
| ☝️ Index finger up | Move mouse cursor |
| 🤌 Thumb + Index pinch | **Left click** |
| 🤏 Thumb + Middle pinch | **Right click** |
| ✌️ Index + Middle (move up/down) | **Scroll** |
| 💍 Ring finger only raised | **Screenshot** (saved to current folder) |
| 🤙 Pinky only raised | **Toggle control on / off** |
| `Q` key | Quit the application |

> **Tip:** Keep your hand 40–70 cm from the camera for best results.

---

## 🛠️ Calibration & Tuning

Open `config.py` to adjust:

| Parameter | Default | What it does |
|-----------|---------|--------------|
| `CAMERA_INDEX` | `0` | Try `1` or `2` if camera not found |
| `SMOOTHING_ALPHA` | `0.20` | Higher = faster but jitterier cursor |
| `PINCH_THRESHOLD` | `0.055` | Lower = harder to trigger left click |
| `RCLICK_THRESHOLD` | `0.060` | Lower = harder to trigger right click |
| `CONTROL_MARGIN` | `0.10` | Margin fraction of frame used as control zone |
| `SCROLL_SENSITIVITY` | `8.0` | Lower = more scroll per gesture |
| `CLICK_DEBOUNCE_FRAMES` | `6` | Frames gesture must be held before firing |

---

## 🐛 Troubleshooting

| Problem | Fix |
|---------|-----|
| "Cannot open camera" | Change `CAMERA_INDEX` in `config.py` to `1` or `2` |
| Cursor jumps wildly | Increase `CLICK_DEBOUNCE_FRAMES`; ensure good lighting |
| Clicks fire too easily | Increase `PINCH_THRESHOLD` (e.g. `0.040`) |
| Low FPS | Lower `CAP_WIDTH`/`CAP_HEIGHT`; close other apps |
| macOS permission error | Grant Accessibility + Screen Recording in System Settings |
| Linux: no mouse movement | Install `xdotool` (see above) |

---

## 🔮 Optional Enhancements (pre-wired hooks)

- **Volume control** — hook into `action_dispatcher.py → dispatch()` using `pycaw` (Windows) or `osascript` (macOS)
- **Second hand** — `gesture_engine.py` tracks up to 2 hands; extend `GestureState` with a `second_hand` field
- **Custom gestures** — add new conditions in `gesture_engine.py → process()` and corresponding actions in `action_dispatcher.py`

---

## 📜 License

MIT — free for personal and commercial use.
