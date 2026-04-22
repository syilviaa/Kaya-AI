# Kaya Health Monitor - Windows Setup Guide

This is the Windows version of the Kaya Health Monitor application. It tracks keystroke patterns to detect burnout and strain.

## Prerequisites

- Python 3.8 or later
- Windows 10 or later

## Installation

### 1. Create a Virtual Environment

```bash
python -m venv .venv
.venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- **PyQt5** - GUI framework
- **PyQtWebEngine** - For rendering the HTML dashboard
- **pynput** - Global keyboard listener
- **pywin32** - Windows API integration
- **pystray** - System tray icon
- **scikit-learn & numpy** - ML for burnout detection

### 3. Post-Installation: Register Windows Services

After installing pywin32, run:

```bash
python Scripts/pywin32_postinstall.py -install
```

Or use:

```bash
pip install pywin32
python -m pip install --upgrade --force-reinstall pywin32
```

## Running the Application

```bash
python main.py
```

The application will:
1. Start a global keyboard listener (monitors all keypresses)
2. Launch a dashboard window showing your health metrics
3. Create a system tray icon to minimize/restore the window

## Features

- **Real-time typing analysis** - Monitors typing speed, patterns, and pauses
- **Burnout detection** - Uses machine learning to detect strain patterns
- **Dashboard** - Shows live metrics and burnout score (0-100)
- **System tray** - Minimize to tray and restore easily
- **Local API** - Metrics available at `http://localhost:9876/metrics`

## Keyboard Monitoring

The application uses `pynput` to listen for keyboard events globally. No special permissions are required on Windows (unlike macOS which requires Accessibility settings).

## Troubleshooting

### "ModuleNotFoundError: No module named 'PyQt5'"

Make sure you activated the virtual environment and installed requirements:
```bash
.venv\Scripts\activate
pip install -r requirements.txt
```

### "No module named 'win32gui'"

Run the pywin32 postinstall:
```bash
python -m pip install --upgrade --force-reinstall pywin32
```

### Window won't appear

Try running with verbose output:
```bash
python -u main.py
```

### Keyboard events not being captured

Check if another application is blocking global keyboard access. Close any accessibility tools or macro recorders.

## Testing

You can test the application without real keyboard input:

1. Navigate to `http://localhost:9876/inject-event?char=a` to inject a keystroke
2. Use `/simulate-typing?text=hello&intensity=1` to simulate typing
3. Check `/metrics` endpoint for current analyzer data

## API Endpoints

- `GET /metrics` - Current burnout metrics
- `GET /training-status` - ML model training status
- `GET /reset` - Clear all data
- `GET /inject-event?char=a` - Inject a keystroke for testing
- `GET /simulate-typing?text=hello&intensity=1` - Simulate typing pattern
- `GET /show-dashboard` - Show the dashboard window
- `GET /quit` - Exit the application

## Database

Event logs and feature vectors are stored in:
```
~/.kaya/kaya_history.db
```

Model data is cached in:
```
~/.kaya/model.pkl
```

## Privacy

- All data is stored locally on your machine
- The local API server only listens on `127.0.0.1:9876` (not accessible from network)
- No data is sent to external servers
- Keyboard monitoring includes only keystroke timing patterns, not the actual text typed
