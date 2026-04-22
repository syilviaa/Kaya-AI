import math
import time
import re
import os
import pickle
from collections import deque
from threading import Lock
import numpy as np
from sklearn.ensemble import IsolationForest
import db

WINDOW_SECONDS       = 300
PAUSE_THRESHOLD      = 2.5
LONG_PAUSE_THRESHOLD = 10.0
CHAR_BUFFER_SIZE     = 200
BASLINE_HISTORY_LEN  = 1000

_FRUSTRATION_PHRASES = {
    "i wanna die": 45,
    "i want to die": 45,
    "end it all": 40,
    "kill me": 35,
    "kms": 50,
    "kys": 50,
    "hate myself": 20,
    "i hate my life": 20,
    "what is wrong with me": 15,
    "i give up": 15,
    "i cant do this": 10,
    "i can't do this": 10,
    "i quit": 10,
    "i hate this": 12,
    "screw this": 10,
    "fml": 15,
    "what the hell": 8,
    "wtf": 5,
    "i'm done": 8,
    "im done": 8,
    "i don't care": 8,
    "i dont care": 8,
    "hate this": 8,
    "so tired": 8,
    "forget it": 6,
    "this is stupid": 8,
    "i cant": 5,
    "i can't": 5,
}

_FRUSTRATION_WORDS = {
    "burden": 12,
    "disappear": 12,
    "vanish": 12,
    "farewell": 10,
    "goodbye": 8,
    "worthless": 12,
    "failure": 10,
    "useless": 10,
    "lonely": 8,
    "isolated": 8,
    "exhausted": 8,
    "empty": 7,
    "alone": 6,
    "tired": 5,
    "guilt": 6,
    "hopeless": 14,
    "helpless": 12,
    "miserable": 10,
    "depressed": 12,
    "desperate": 12,
    "broken": 10,
    "defeated": 10,
    "trapped": 12,
    "suffocating": 12,
    "spiraling": 12,
    "drowning": 12,
    "sinking": 10,
    "crumbling": 10,
    "drained": 8,
    "numb": 8,
    "cynical": 8,
    "resentful": 8,
    "overwhelmed": 10,
    "frazzled": 8,
    "autopilot": 6,
    "quit": 6,
    "resigned": 8,
    "bitter": 7,
    "unmotivated": 8,
    "apathetic": 8,
    "disconnected": 8,
    "detached": 8,
    "shutdown": 8,
    "burned": 6,
    "crying": 8,
    "tears": 6,
    "panic": 12,
    "anxious": 10,
    "shaking": 10,
    "tense": 5,
    "agitated": 8,
    "irritable": 7,
    "furious": 10,
    "angry": 5,
    "frustrated": 7,
    "stressed": 6,
    "urgent": 5,
    "deadline": 4,
    "racing": 5,
    "stuck": 5,
    "paralyzed": 8,
    "scattered": 6,
    "confused": 5,
    "lost": 6,
    "failing": 8,
    "inadequate": 10,
    "sorry": 3,
}

MIN_VECTORS_FOR_ML = 20
UPDATE_INTERVAL    = 30
SCORE_DECAY_RATE   = 0.96

MODEL_DIR  = os.path.expanduser("~/.kaya")
MODEL_FILE = os.path.join(MODEL_DIR, "model.pkl")


class Analyzer:
    def __init__(self):
        db.init_db()
        self._lock = Lock()
        self._events: deque = deque()
        self._intervals: deque = deque(maxlen=500)
        self._pauses: deque = deque()
        self._char_buffer: deque = deque(maxlen=CHAR_BUFFER_SIZE)
        self._app_name: str = "unknown"
        self._key_downs = {}
        self._hold_times = deque(maxlen=200)
        self._digraphs = deque(maxlen=200)
        self._undo_count = 0
        self._arrow_count = 0
        self._last_event_ts = time.time()
        self._start_time = time.time()
        self._history = {
            "code":    deque(maxlen=BASLINE_HISTORY_LEN),
            "prose":   deque(maxlen=BASLINE_HISTORY_LEN),
            "passive": deque(maxlen=BASLINE_HISTORY_LEN),
        }
        self._models = {"code": None, "prose": None, "passive": None}
        self._last_ts: float | None = None
        self._score: float = 0.0
        self._last_inactive_check: float = time.time()
        self._last_vector_update: float = time.time()
        self._keypress_count: int = 0
        self._demo_mode: bool = False
        self._demo_start_time: float = 0.0
        self._keyword_score: float = 0.0
        self._keyword_matches: list = []
        self._keyword_last_update: float = 0.0
        self._prev_keyword_matches: list = []
        self._last_train_time: float = 0.0
        self._vectors_since_train: int = 0
        self._load_model()

    def reset(self):
        with self._lock:
            self._events.clear()
            self._intervals.clear()
            self._pauses.clear()
            self._char_buffer.clear()
            self._key_downs.clear()
            self._hold_times.clear()
            self._history = {
                "code":    deque(maxlen=BASLINE_HISTORY_LEN),
                "prose":   deque(maxlen=BASLINE_HISTORY_LEN),
                "passive": deque(maxlen=BASLINE_HISTORY_LEN),
            }
            self._models = {"code": None, "prose": None, "passive": None}
            self._last_ts = None
            self._score = 0.0
            self._keypress_count = 0
            self._undo_count = 0
            self._arrow_count = 0
            self._keyword_score = 0.0
            self._keyword_matches = []
            self._keyword_last_update = 0.0
            self._prev_keyword_matches = []

    def ingest(self, event: dict):
        with self._lock:
            ts = event["ts"]
            is_down = event["is_down"]
            keycode = event["keycode"]

            db.log_event(ts, keycode, int(is_down), int(event["is_backspace"]), event["app_name"], event["modifiers"])

            if is_down and event["char"]:
                print(f"[ANALYZER] Ingested: '{event['char']}' | Total events: {self._keypress_count + 1}", flush=True)

            if is_down:
                self._keypress_count += 1
                self._prune(ts)
                self._events.append((ts, event["is_backspace"]))

                if "app_name" in event and event["app_name"]:
                    self._app_name = event["app_name"]

                if self._last_ts is not None:
                    gap = ts - self._last_ts
                    if gap < LONG_PAUSE_THRESHOLD:
                        self._intervals.append(gap)
                        if gap >= PAUSE_THRESHOLD:
                            self._pauses.append(ts)
                self._last_ts = ts

                if keycode in (123, 124, 125, 126):
                    self._arrow_count += 1

                is_cmd = event["modifiers"] & (1 << 20)
                is_z = event["char"] == 'z' or event["char"] == 'Z' or keycode == 6
                if is_cmd and is_z:
                    self._undo_count += 1

                if event["char"]:
                    self._char_buffer.append(event["char"])

                self._key_downs[keycode] = ts
            else:
                if keycode in self._key_downs:
                    hold_time = ts - self._key_downs.pop(keycode)
                    if hold_time < 2.0:
                        self._hold_times.append(hold_time)

            if is_down and len(self._events) >= 5:
                self._record_feature_vector(ts)

    def get_score(self) -> float:
        with self._lock:
            return round(min(100.0, self._compute_score()), 1)

    def get_training_status(self) -> dict:
        with self._lock:
            mode = self._detect_mode()
            if self._demo_mode:
                collected = 100
            else:
                collected = min(100, self._keypress_count * 5)
            return {
                "current_mode":     mode,
                "keypresses":       self._keypress_count,
                "vectors_collected": collected,
                "vectors_needed":   100,
                "models_ready":     {m: self._models[m] is not None for m in self._models},
                "app_name":         self._app_name,
                "demo_mode":        self._demo_mode,
            }

    def enable_demo_mode(self, enable: bool = True):
        with self._lock:
            self._demo_mode = enable
            if enable:
                self._demo_start_time = time.time()
                self._score = 0.0

    def get_metrics(self) -> dict:
        with self._lock:
            now = time.time()
            self._prune(now)

            if self._demo_mode:
                elapsed = now - self._demo_start_time
                t = min(1.0, elapsed / 90.0)
                ease = t * t * (3.0 - 2.0 * t)
                score  = round(ease * 86, 1)
                s_bs   = round(ease * 78, 1)
                s_rh   = round(ease * 73, 1)
                s_pa   = round(ease * 68, 1)
                s_sp   = round(ease * 75, 1)
                s_kw   = round(ease * 82, 1)
                wpm    = round(max(10.0, 56.0 - ease * 42.0), 1)
                keys   = int(ease * 450)
                pauses = int(ease * 18)
                reasons = []
                if ease > 0.03: reasons.append("Strain building")
                if s_bs > 45:   reasons.append("High backspace rate")
                if s_rh > 45:   reasons.append("Irregular rhythm")
                if s_pa > 45:   reasons.append("Frequent pausing")
                if s_kw > 55:   reasons.append("Frustrated typing detected")
                return {
                    "total_keys":      keys,
                    "backspace_ratio": round(ease * 18, 1),
                    "pauses":          pauses,
                    "rhythm_cv":       round(ease * 0.8, 2),
                    "current_wpm":     wpm,
                    "baseline_wpm":    56.0,
                    "hold_time":       90.0,
                    "burnout_score":   score,
                    "current_mode":    "prose",
                    "app_name":        self._app_name,
                    "s_backspace":     s_bs,
                    "s_rhythm":        s_rh,
                    "s_pauses":        s_pa,
                    "s_speed":         s_sp,
                    "s_keyword":       s_kw,
                    "active_reasons":  reasons,
                    "keyword_alert":   [],
                    "is_learning":     False,
                }

            is_learning = self._keypress_count < 20

            total = len(self._events)
            backspaces = sum(1 for _, bs in self._events if bs)
            br = backspaces / max(total, 1)
            wpm = self._current_wpm(now)
            baseline_wpm = self._get_baseline_wpm(self._detect_mode())
            hold_mean = float(np.mean(self._hold_times)) if self._hold_times else 0.0

            if is_learning:
                score = 0.0
                sv_backspace = sv_rhythm = sv_pauses = sv_speed = sv_frustration = 0.0
                active_reasons = []
                keyword_alert = []
            else:
                sv_backspace = min(100.0, br * 500)
                sv_rhythm    = min(100.0, self._rhythm_cv() * 100)
                pause_rate   = len(self._pauses) / (WINDOW_SECONDS / 60.0)
                sv_pauses    = min(100.0, pause_rate * 10)
                if baseline_wpm > 5 and wpm < baseline_wpm:
                    sv_speed = min(100.0, ((baseline_wpm - wpm) / baseline_wpm) * 150)
                else:
                    sv_speed = 0.0

                frustration_base = self._detect_gibberish() * 0.3
                undo_factor      = min(15.0, (self._undo_count / 5.0) * 5.0)
                arrow_factor     = min(5.0,  (self._arrow_count / 100.0) * 2.5)

                fresh_kw, fresh_matches = self._detect_keywords()
                if fresh_kw > 0:
                    self._keyword_score = max(self._keyword_score, fresh_kw)
                    self._keyword_matches = fresh_matches
                    self._keyword_last_update = now
                elif self._keyword_last_update > 0:
                    elapsed_kw = now - self._keyword_last_update
                    self._keyword_score = max(0.0, self._keyword_score * (0.5 ** (elapsed_kw / 120.0)))

                keyword_score  = self._keyword_score
                sv_frustration = min(100.0, frustration_base + undo_factor + arrow_factor + keyword_score)

                keyword_alert = []
                if fresh_matches and fresh_matches != self._prev_keyword_matches:
                    keyword_alert = fresh_matches
                    self._prev_keyword_matches = fresh_matches[:]

                raw_score = (sv_backspace * 0.25 + sv_rhythm * 0.20 +
                             sv_pauses * 0.20 + sv_speed * 0.20 + sv_frustration * 0.15)
                self._score = 0.35 * raw_score + 0.65 * self._score
                score = min(100.0, self._score)

                active_reasons = []
                if sv_backspace > 50: active_reasons.append("High backspace rate")
                if sv_rhythm    > 50: active_reasons.append("Irregular rhythm")
                if sv_pauses    > 50: active_reasons.append("Frequent pausing")
                if keyword_score > 0 and self._keyword_matches:
                    kw_str = ", ".join(f'"{w}"' for w in self._keyword_matches[:3])
                    active_reasons.append(f"Frustration: {kw_str}")
                elif sv_frustration > 30:
                    active_reasons.append("Frustrated typing detected")

            return {
                "total_keys":      total,
                "backspace_ratio": round(br * 100, 1),
                "pauses":          len(self._pauses),
                "rhythm_cv":       round(min(100.0, self._rhythm_cv() * 100), 1),
                "current_wpm":     round(wpm, 1),
                "baseline_wpm":    round(baseline_wpm, 1),
                "hold_time":       round(hold_mean * 1000, 0),
                "burnout_score":   round(score, 1),
                "current_mode":    self._detect_mode(),
                "app_name":        self._app_name,
                "s_backspace":     round(sv_backspace, 1),
                "s_rhythm":        round(sv_rhythm, 1),
                "s_pauses":        round(sv_pauses, 1),
                "s_speed":         round(sv_speed, 1),
                "s_keyword":       round(sv_frustration, 1),
                "active_reasons":  active_reasons,
                "keyword_alert":   keyword_alert,
                "is_learning":     is_learning,
            }

    def _load_model(self):
        if os.path.exists(MODEL_FILE):
            try:
                with open(MODEL_FILE, "rb") as f:
                    data = pickle.load(f)
                    self._history = data.get("history", self._history)
                    self._models = data.get("models", self._models)
                    print(f"Loaded persisted model from {MODEL_FILE}", flush=True)
            except Exception as e:
                print(f"Could not load persisted model: {e}", flush=True)

    def _save_model(self):
        try:
            os.makedirs(MODEL_DIR, exist_ok=True)
            with open(MODEL_FILE, "wb") as f:
                pickle.dump({"history": self._history, "models": self._models}, f)
        except Exception as e:
            print(f"Could not save model: {e}", flush=True)

    def _get_signal_score(self, mode: str, feature_idx: int, feature_value: float) -> float:
        model_data = self._models.get(mode)
        if model_data is None:
            return 50.0
        mean = model_data["mean"][feature_idx]
        std  = model_data["std"][feature_idx]
        if std == 0:
            return 50.0
        z = (feature_value - mean) / std
        score = 50.0 + z * 15.0
        return np.clip(score, 0.0, 100.0)

    def _prune(self, now: float):
        cutoff = now - WINDOW_SECONDS
        while self._events and self._events[0][0] < cutoff:
            self._events.popleft()
        while self._pauses and self._pauses[0] < cutoff:
            self._pauses.popleft()

    def _detect_mode(self) -> str:
        mode_from_app = self._detect_mode_from_app(self._app_name)
        if mode_from_app:
            return mode_from_app
        chars = "".join(self._char_buffer)
        if not chars:
            return "prose"
        code_chars = sum(1 for c in chars if c in "{}[];=<>#$/\\()_")
        if code_chars > len(chars) * 0.05:
            return "code"
        return "prose"

    def _detect_mode_from_app(self, app_name: str) -> str | None:
        if not app_name or app_name == "unknown":
            return None
        code_apps    = {"Terminal", "Code", "Xcode", "PyCharm", "Sublime", "Vim", "Emacs", "IntelliJ"}
        passive_apps = {"YouTube", "QuickTime Player", "VLC", "Netflix", "Safari", "Chrome", "Firefox", "Discord"}
        prose_apps   = {"Pages", "Notes", "Slack", "Mail", "iMessage", "Word", "Google Docs"}
        for app in code_apps:
            if app.lower() in app_name.lower():
                return "code"
        for app in passive_apps:
            if app.lower() in app_name.lower():
                return "passive"
        for app in prose_apps:
            if app.lower() in app_name.lower():
                return "prose"
        return None

    def _detect_gibberish(self) -> float:
        chars = "".join(self._char_buffer).lower()
        if len(chars) < 5:
            return 0.0
        vowels = sum(1 for c in chars if c in "aeiouy")
        v_density = vowels / len(chars)
        consonant_run = 0
        max_run = 0
        for c in chars:
            if c.isalpha() and c not in "aeiouy":
                consonant_run += 1
                max_run = max(max_run, consonant_run)
            else:
                consonant_run = 0
        score = 0.0
        if v_density < 0.25: score += 40.0
        if v_density < 0.15: score += 40.0
        if max_run >= 5:     score += 40.0
        if max_run >= 8:     score += 60.0
        return min(100.0, score)

    def _detect_keywords(self):
        text = "".join(self._char_buffer).lower()
        if len(text) < 3:
            return 0.0, []
        score = 0.0
        matched = []
        for phrase, weight in _FRUSTRATION_PHRASES.items():
            if phrase in text:
                score += weight
                matched.append(phrase)
        words = set(re.findall(r'\b[a-z]+\b', text))
        for word, weight in _FRUSTRATION_WORDS.items():
            if word in words:
                score += weight
                matched.append(word)
        return min(100.0, score), matched

    def _extract_features(self, now: float) -> list[float]:
        latency_mean = np.mean(self._intervals) if self._intervals else 0.0
        wpm          = self._current_wpm(now)
        session_min  = WINDOW_SECONDS / 60.0
        pause_rate   = len(self._pauses) / session_min
        total        = len(self._events)
        backspaces   = sum(1 for _, bs in self._events if bs)
        br           = backspaces / max(total, 1)
        cv           = self._rhythm_cv()
        gs           = self._detect_gibberish()
        kv           = np.std(self._intervals) if len(self._intervals) > 1 else 0.0
        hold_mean    = np.mean(self._hold_times) if self._hold_times else 0.0
        undo_rate    = self._undo_count / max(total, 1)
        arrow_rate   = self._arrow_count / max(total, 1)
        return [latency_mean, wpm, pause_rate, br, cv, gs, kv, hold_mean, undo_rate, arrow_rate]

    def _record_feature_vector(self, now: float):
        if len(self._events) < 5:
            return
        mode = self._detect_mode()
        vec = self._extract_features(now)
        self._history[mode].append(vec)
        self._vectors_since_train += 1
        db.log_features(mode, vec[1], vec[3], vec[4], vec[7], vec[3], self._score)
        enough_data = len(self._history[mode]) >= MIN_VECTORS_FOR_ML
        enough_new  = self._vectors_since_train >= 20
        enough_time = (now - self._last_train_time) >= 60.0
        if enough_data and enough_new and enough_time:
            self._train_model(mode)
            self._last_train_time = now
            self._vectors_since_train = 0

    def _train_model(self, mode: str):
        data = np.array(self._history[mode])
        if data.shape[0] < MIN_VECTORS_FOR_ML:
            return
        mean      = np.mean(data, axis=0)
        std       = np.std(data, axis=0) + 1e-6
        norm_data = (data - mean) / std
        model     = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)
        model.fit(norm_data)
        self._models[mode] = {"mean": mean, "std": std, "model": model}
        self._save_model()
        print(f"Trained model for mode '{mode}' ({data.shape[0]} vectors)", flush=True)

    def _current_wpm(self, now: float) -> float:
        cutoff = now - 60
        recent = sum(1 for ts, bs in self._events if ts >= cutoff and not bs)
        return recent / 5.0

    def _get_baseline_wpm(self, mode: str) -> float:
        if self._models[mode] is not None:
            return self._models[mode]["mean"][1]
        return 0.0

    def _rhythm_cv(self) -> float:
        vals = [v for v in self._intervals if v < 0.5]
        if len(vals) < 5:
            return 0.0
        mean = sum(vals) / len(vals)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in vals) / len(vals)
        return math.sqrt(variance) / mean

    def _compute_score(self) -> float:
        now   = time.time()
        total = len(self._events)
        if total < 5:
            elapsed_min  = (now - self._last_inactive_check) / 60.0
            self._score  = max(0.0, self._score * (SCORE_DECAY_RATE ** elapsed_min))
            self._last_inactive_check = now
            return self._score
        self._last_inactive_check = now
        mode = self._detect_mode()
        vec  = self._extract_features(now)
        raw_anomaly_score = 0.0
        if self._models[mode] is not None:
            model_data = self._models[mode]
            norm_vec   = (np.array(vec) - model_data["mean"]) / model_data["std"]
            sf         = model_data["model"].decision_function([norm_vec])[0]
            risk = 0.0
            if sf < 0:
                risk = min(100.0, (-sf / 0.3) * 100.0)
            raw_anomaly_score = risk
        else:
            br           = vec[3]
            s_backspace  = min(25.0, br * 250)
            cv           = self._rhythm_cv()
            s_rhythm     = min(20.0, cv * 20.0)
            pause_rate   = vec[2]
            s_pause      = min(20.0, pause_rate * 6.67)
            raw_anomaly_score = s_backspace + s_rhythm + s_pause
        gs           = self._detect_gibberish()
        undo_penalty = min(20.0, (self._undo_count / 5.0) * 10.0)
        arrow_penalty = min(15.0, (self._arrow_count / 100.0) * 5.0)
        hold_penalty = 0.0
        if self._hold_times:
            avg_hold = np.mean(self._hold_times)
            if avg_hold > 0.15:
                hold_penalty = min(20.0, (avg_hold - 0.15) * 200.0)
        smash_penalty = 0.0
        if vec[1] > 45 and gs > 35:
            smash_penalty = (gs / 100.0) * 30.0
        final_raw   = min(100.0, raw_anomaly_score + smash_penalty + undo_penalty + arrow_penalty + hold_penalty)
        self._score = 0.6 * final_raw + 0.4 * self._score
        return self._score
