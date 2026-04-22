# Implementation: ML-Based User-Personalized Keystroke Anomaly Detection

## Overview
The keystroke analyzer now uses machine learning (Isolation Forest) to build personalized user baselines and detect anomalies relative to each individual's normal typing patterns.

## Key Features

### 1. User-Personalized ML Baselines
- **Training Process**: Models are trained after collecting 20 feature vectors (one every 30 seconds of typing) per mode
- **Feature Vector**: 7 features extracted per 30-second window:
  1. Latency mean (inter-keystroke timing)
  2. WPM (words per minute)
  3. Pause rate (pauses per minute)
  4. Backspace ratio (% of keys that are backspaces)
  5. Rhythm CV (coefficient of variation in timing)
  6. Gibberish score (consonant clustering, vowel density)
  7. Keystroke variance (std dev of inter-keystroke times)

- **Training**: Isolation Forest with 100 estimators, 10% contamination
- **Persistence**: Models saved to `~/.kaya/model.pkl` after training
- **Cold Start**: Returning users skip re-training if persistent model exists

### 2. Three Context Modes

Each mode gets its own model to avoid comparing different typing contexts:

| Mode | Indicators | Examples |
|------|-----------|----------|
| **💻 Coding** | Curly braces, brackets, equals | Terminal, Code, Xcode, PyCharm |
| **✍️ Writing** | Regular text, no symbols | Notes, Pages, Slack, Mail |
| **👁 Watching** | Very sparse typing (arrows, space) | Safari, YouTube, VLC, Netflix |

Mode is determined by:
1. **App-based detection** (fastest): Check active app name
2. **Heuristic fallback**: Analyze character buffer for code symbols

### 3. Personalized Signal Scoring

All 5 signals use z-score normalization relative to user's learned baseline:

```
score = 50 + (value - user_mean) / user_std * 15
```

- **Score 50**: User's normal/baseline
- **Score 0-50**: Below normal (calm, slow typing)
- **Score 50-100**: Above normal (stressed, irregular typing)

### 4. Always-On Detection

The 5 signals now detect:
1. **Backspace rate** — percentage of keys deleted
2. **Rhythm irregularity** — variance in typing tempo
3. **Pause density** — frequency of pauses
4. **Speed vs baseline** — current WPM vs learned normal
5. **Frustration signals** — gibberish typing detection

### 5. Training Progress UI

When the app launches, users see:
- **Training Banner** (yellow alert bar): "Learning your patterns…"
- **Per-mode progress bars**: Shows 0-20 vectors collected
- **Mode badge**: Shows current app context (💻/✍️/👁)

Banner automatically hides when training is complete (all 3 modes ready).

## API Endpoints

### `/training-status`
Returns current training progress:
```json
{
  "current_mode": "code",
  "keypresses": 1540,
  "vectors_collected": 8,
  "vectors_needed": 20,
  "models_ready": {
    "code": false,
    "prose": false,
    "passive": false
  },
  "app_name": "Code"
}
```

### `/metrics`
Returns current metrics with personalized signal scores:
```json
{
  "burnout_score": 23.4,
  "current_mode": "code",
  "app_name": "Code",
  "s_backspace": 52.3,      // User-relative
  "s_rhythm": 51.8,         // User-relative
  "s_pauses": 50.0,         // User-relative
  "s_speed": 48.2,          // User-relative
  "s_keyword": 35.0         // User-relative
}
```

## Files Modified

### analyzer.py
- **7 features** extracted per vector (was 4)
- **3 modes** supported (code, prose, passive)
- **Personalized scoring** via `_get_signal_score()`
- **Model persistence** via `_load_model()` and `_save_model()`
- **App-aware detection** via `_detect_mode_from_app()`
- **Training status** via `get_training_status()`

### listener.py
- **App name detection** using `NSWorkspace.frontmostApplication()`
- **Better error handling** for system calls
- **Passes app_name** in every event payload

### server.py
- **New `/training-status` endpoint** for training progress

### static/index.html
- **Training banner** with per-mode progress bars
- **Mode badge** in header showing current context
- **Updated polling** to check training status
- **Personalized signal labels** (score relative to baseline)

## Usage Notes

1. **First Run**: App will show training banner. Users need to type for ~10 minutes (across all modes) to collect 20 vectors per mode.

2. **Mode Switching**: The mode badge automatically updates as user switches apps. Type in different contexts (code editor, text editor, browser) to train all modes.

3. **Returning Users**: Model loads from disk automatically. Personalization starts immediately.

4. **Anomaly Detection**: When user types unusually (fast, many backspaces), signal scores spike above 50, indicating deviation from baseline.

## Example Workflow

1. **Day 1**: User launches app, sees training banner
2. **Day 1**: User codes for 10 minutes → 20 vectors collected → Code model trained
3. **Day 1**: User writes docs for 10 minutes → Writing model trained
4. **Day 1**: User watches video with some typing → Watching model trained
5. **Day 1 end**: Training banner hidden, all models ready
6. **Day 2**: User returns, model loads from disk instantly
7. **Any day**: Frantic typing detected as anomaly, burnout score rises

## Verification

All features tested with simulated input:
- ✅ Models train after 20 vectors per mode
- ✅ Personalized scores calculated correctly
- ✅ Anomalies detected (high backspace rate, fast typing)
- ✅ Mode switching works (Code/Notes/Safari)
- ✅ Model persistence verified
- ✅ Training progress UI implemented
- ✅ All endpoints responding correctly
