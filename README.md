# Kaya

Kaya is a local-only Windows application that monitors typing patterns to detect early signs of stress, burnout, and ADHD. It operates completely on-device, only tracking keystroke metadata (like inter-keystroke latency and undo rates) rather than text content, ensuring privacy.

## Features

- **Privacy-First Data Collection**: Processes all data locally. Keystroke content is never logged, stored, or transmitted.
- **Anomaly Detection**: Uses an Isolation Forest machine learning model to establish a personal typing baseline and detect deviations (e.g., increased backspace rate, erratic arrow key usage).
- **Context-Aware Profiling**: Differentiates between typing modes (coding, prose, passive) to adjust baseline expectations based on the type of work currently being done.
- **Native macOS Integration**: Uses PyObjC and AppKit for a native feel, complete with macOS vibrancy window effects, tracking within a local dashboard, and a menu bar widget.

## Tech Stack

- **Core Logic**: Python 3
- **Machine Learning**: `scikit-learn` (Isolation Forest), `numpy`
- **Data Storage**: Local SQLite (`db.py`)
- **OS Integration**: CoreGraphics/Quartz APIs, `AppKit`, `PyObjC`, `WebKit`
- **UI**: Vanilla HTML/CSS/JS served via an internal lightweight HTTP server

## Installation

### Prerequisites
- macOS
- Python 3.9+
- Accessibility permissions granted to your terminal emulator (System Settings > Privacy & Security > Accessibility)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/syilviaa/Kaya-AI.git
   cd Kaya-AI
   ```

2. **Set up the virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Start the main application:
```bash
python main.py
```

The app will launch the dashboard upon first opening and run passively in the background. You can assess your real-time burnout signals locally.

## Project Structure

- `main.py` - Application entry point. Checks accessibility permissions and launches system threads.
- `app.py` - Manages macOS UI lifecycle, dashboard state, styling, and webview rendering.
- `analyzer.py` - Defines and calculates ML features (Rhythm CV, Key Hold Time, Cmd-Z rate) and analyzes standard deviations and Z-scores against personal baselines.
- `listener.py` - CoreGraphics event tap listener. Extracts timing and coordinate metadata from user input.
- `server.py` - Local loopback server (port 9876) serving endpoints like `/metrics` and `/training-status` to the frontend.
- `db.py` - Handles persistent state cross-session.
- `static/` - Frontend codebase:
  - `index.html` - The comprehensive setup and primary dashboard view.
  - `panel.html` - Condensed status UI intended for the menu bar popover.
