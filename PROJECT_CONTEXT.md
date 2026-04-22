# Kaya – Project Context & Architecture

Kaya is a privacy-first, local-only macOS application designed to detect early signs of burnout, stress, and ADHD by analyzing typing patterns. It uses machine learning (Isolation Forest) to compare current typing behavior against a personalized baseline, all without ever reading or storing keystroke content.

## 🛠 Tech Stack
- **Backend**: Python 3
- **Database**: SQLite (via `db.py`)
- **GUI**: macOS Native (via `PyObjC`), `AppKit`, `WebKit` (for UI rendering)
- **ML**: `scikit-learn` (Isolation Forest), `numpy`
- **Frontend**: Vanilla HTML/CSS/JS (served locally)
- **Monitoring**: ApplicationServices (Accessibility API) for keyboard events

## 🏗 System Architecture

The app follows a decoupled architecture where the logic and UI communicate via a local HTTP server:

1. **Listener (`listener.py`)**: Captures global keyboard event metadata (KeyDown/KeyUp, timestamps, key codes, modifiers).
2. **Analyzer (`analyzer.py`)**: 
   - Receives events and extracts high-fidelity features:
     - **Temporal**: Inter-keystroke latency (IKL) and **Key Hold Time**.
     - **Frustration**: **Undo rate (Cmd-Z)** and **Arrow key micro-adjustments**.
     - **Context**: Backspace rate, Rhythm CV, Pause density.
   - Classifies context into "modes" (coding, prose, passive).
   - Trains an Isolation Forest model per mode to detect anomalies.
3. **Database (`db.py`)**: Persistent SQLite storage for raw events and calculated features (cross-session).
4. **Server (`server.py`)**: A tiny local HTTP server (port 9876) that exposes metrics as JSON.
5. **App Delegate (`app.py`)**: Manages the macOS lifecycle and windows.
   - **Main Window**: Full dashboard (`index.html`) used for setup and deep analysis.
   - **Floating Panel**: Compact status view (`panel.html`) accessible via the menu bar.
5. **Main (`main.py`)**: Coordinates initialization and starts all threads.

## 📂 File Structure

- `main.py`: Entry point. System permission checks and service initialization.
- `app.py`: macOS window management, transparency, and vibrancy effects.
- `analyzer.py`: ML logic, z-score normalization, and burnout scoring algorithms.
- `listener.py`: Global event tap using macOS CoreGraphics/Quartz.
- `server.py`: Request handling for UI and inter-process communication.
- `static/`:
  - `index.html`: The comprehensive dashboard and onboarding flow.
  - `panel.html`: The compact, high-level status view for the menu bar.

## 💡 Key Mechanisms

### UI Communication
The UI (HTML/JS) polls the local server for metrics:
- `GET /metrics`: Current burnout score and underlying signals.
- `GET /training-status`: Progress of ML baseline collection.
- `GET /show-dashboard`: Instructs the Python app to bring the main window to focus.

### Anomaly Detection
Instead of looking for specific "stressed" typing, the system looks for **deviations from your normal self**.
- It collects a baseline (20+ samples) for each mode.
- It uses Z-scores to normalize signals like "Backspace rate" relative to your own average.
- If signals deviate significantly, the `burnout_score` (0-100) increases.

## 🚀 How to Run
```bash
# Ensure you have accessibility permissions granted to your terminal
.venv/bin/python main.py
```

## ⚠️ Important Implementation Notes
- **Window Management**: The app uses `NSWindowStyleMaskFullSizeContentView` for a modern, borderless look.
- **Vibrancy**: macOS vibrancy is applied at the window level behind the transparent WebKit view.
- **Specificity**: In `index.html`, use `!important` for visibility toggling (`.hidden`) to ensure it overrides ID-based display rules.
