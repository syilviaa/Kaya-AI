# Window Separation Fix - Dashboard and App

## Problem
The dashboard and app window were showing mixed content:
- Both main window and floating panel were loading the same full HTML
- Created a confusing UI with overlapping/duplicate elements
- No clear separation between dashboard view and compact status view

## Solution
Separated the UI into two distinct views:

### 1. **Main Window (Dashboard View)**
- **File**: `index.html`
- **Purpose**: Full dashboard with complete statistics and controls
- **Content**:
  - Large burnout score display
  - All 5 signal indicators
  - Training progress banner
  - Activity feed
  - Full controls and settings
- **URL**: `http://localhost:9876/?view=dashboard`
- **Window Style**: Regular window with title bar and controls
- **Visibility**: Shows in dock, appears on launch

### 2. **Floating Panel (Compact Status View)**
- **File**: `panel.html` (NEW)
- **Purpose**: Lightweight status indicator for menu bar
- **Content**:
  - Burnout score (large, prominent)
  - Current mode indicator
  - WPM and app name
  - Quick action buttons (Open Dashboard, Take Break)
- **URL**: `http://localhost:9876/?view=panel`
- **Window Style**: Floating panel, stays on top
- **Visibility**: Hidden by default, shown via menu bar icon

## Implementation Details

### app.py Changes
```python
# Main window loads dashboard view
url = NSURL.URLWithString_("http://127.0.0.1:9876/?view=dashboard")

# Panel loads compact view
url = NSURL.URLWithString_("http://127.0.0.1:9876/?view=panel")
```

### server.py Changes
```python
# Parse view parameter from URL
view = query_params.get('view', ['dashboard'])[0]

# Serve different HTML based on view
if view == "panel":
    html_path = os.path.join(_static_dir, "panel.html")
else:
    html_path = os.path.join(_static_dir, "index.html")
```

### New Files
- **panel.html**: Compact 390×180px status view
  - Minimal, focused UI
  - Quick stats and actions
  - Responsive to score changes

## User Experience

### Startup Sequence
1. App launches → **Main Dashboard Window** appears
   - Full dashboard in center of screen
   - Shows all metrics and training progress
   - Can resize, minimize, move freely
   
2. Click "Start Monitoring" → **Transitions to Menu Bar Mode**
   - Dashboard window closes/minimizes to dock
   - App moves to menu bar (see ⬤ icon)
   - Click menu bar icon to show **Floating Panel**
   
3. **Floating Panel** (390×180px)
   - Shows at menu bar level
   - Always visible, never overlaps with work
   - Shows current score and stats
   - Button to "Open Dashboard" for full view

## Visual Comparison

### Dashboard View (index.html)
```
┌─────────────────────────────────┐
│ KAYA                  local only │
├─────────────────────────────────┤
│ 🟢 42 / 100                     │
│ Within normal range             │
├─────────────────────────────────┤
│ ▓▓▓▓░░░░░  Backspace rate       │
│ ▓▓▓░░░░░░  Rhythm irregularity  │
│ ▓▓░░░░░░░  Pause density        │
│ ▓▓▓░░░░░░  Speed vs baseline    │
│ ░░░░░░░░░  Frustration signals  │
├─────────────────────────────────┤
│ Activity Feed                   │
│ 14:32 Backspace rate        +2.5│
│ 14:28 Speed drop            -1.2│
├─────────────────────────────────┤
│ Speed: 45 WPM │ Keys: 1240 │ 12 │
├─────────────────────────────────┤
│ [Take a break] [Reset] [Quit]   │
└─────────────────────────────────┘
```

### Panel View (panel.html)
```
┌─────────────────┐
│      KAYA       │
├─────────────────┤
│                 │
│        42       │
│  burnout score  │
│   Normal        │
│                 │
├─────────────────┤
│  💻  │  45 WPM  │
│ VSCode          │
├─────────────────┤
│ [Open Dashboard]│
│ [ Take Break ]  │
└─────────────────┘
```

## Technical Architecture

```
┌──────────────────────────────────────────────────┐
│  macOS Application (main.py)                      │
│  ┌────────────────────────────────────────────┐  │
│  │ AppDelegate (app.py)                        │  │
│  │  ├─ Main Window (390×620)                  │  │
│  │  │  └─ WKWebView → Dashboard (index.html)  │  │
│  │  │                                          │  │
│  │  └─ Floating Panel (390×180)               │  │
│  │     └─ WKWebView → Panel (panel.html)      │  │
│  └────────────────────────────────────────────┘  │
│         ↓                ↓                        │
│  ┌──────────────────────────────────────────┐   │
│  │  Local HTTP Server (server.py)            │   │
│  │  http://localhost:9876                    │   │
│  │  ├─ /?view=dashboard  → index.html        │   │
│  │  ├─ /?view=panel      → panel.html        │   │
│  │  ├─ /metrics         → JSON               │   │
│  │  └─ /training-status → JSON               │   │
│  └──────────────────────────────────────────┘   │
│         ↓                                        │
│  ┌──────────────────────────────────────────┐   │
│  │  Analyzer (analyzer.py)                  │   │
│  │  Machine Learning Models                 │   │
│  └──────────────────────────────────────────┘   │
└──────────────────────────────────────────────────┘
```

## Benefits

✅ **Clear Separation of Concerns**
   - Dashboard = detailed analysis and training
   - Panel = quick status check

✅ **Better User Experience**
   - No overlapping windows
   - Can keep panel in view while working
   - Full dashboard available when needed

✅ **Responsive Design**
   - Each view optimized for its size
   - Panel minimal, fast to render
   - Dashboard can expand/shrink

✅ **Non-intrusive Monitoring**
   - Panel doesn't interfere with work
   - Floating window on top, stays accessible
   - Can focus on app + see status simultaneously

## Testing

### View Separation
```bash
# Dashboard view
curl 'http://127.0.0.1:9876/?view=dashboard' | grep "<title>"
# Output: <title>Kaya</title>

# Panel view
curl 'http://127.0.0.1:9876/?view=panel' | grep "<title>"
# Output: <title>Kaya Panel</title>
```

### Window Behavior
1. **On Launch**
   - Main window appears with full dashboard
   - Shows training progress, all metrics
   - Can resize, minimize, move

2. **After "Start Monitoring"**
   - Main window hides (or minimizes)
   - Menu bar icon appears (⬤ with score)
   - Click icon to show floating panel

3. **Panel Features**
   - Draggable header for repositioning
   - Quick access buttons
   - Auto-updates every 2 seconds
   - Non-intrusive positioning

## Files Modified

### app.py
- Main window URL: `?view=dashboard`
- Panel window URL: `?view=panel`

### server.py
- URL parsing for `view` parameter
- Conditional HTML serving based on view

### New file: panel.html
- Compact 390×180px layout
- Score display + quick stats
- Action buttons
- Real-time polling

### index.html
- Unchanged (still serves as full dashboard)
- Now loaded only when `?view=dashboard`

## Summary

The application now has:
✅ **Clear window separation** - dashboard vs panel
✅ **Non-intrusive UI** - floating panel doesn't block work
✅ **Full features available** - dashboard for detailed analysis
✅ **Quick checks** - panel for status at a glance
✅ **Professional appearance** - organized, intentional design

