import time
import platform
from threading import Lock, Thread


def get_active_window_name():
    try:
        if platform.system() == "Windows":
            import win32gui
            window = win32gui.GetForegroundWindow()
            window_title = win32gui.GetWindowText(window)
            import psutil
            try:
                pid     = win32gui.GetWindowThreadProcessId(window)[1]
                process = psutil.Process(pid)
                app_name = process.name().replace('.exe', '')
            except:
                app_name = window_title.split(' - ')[-1] if ' - ' in window_title else window_title
            return app_name or "unknown"
        else:
            return "unknown"
    except:
        return "unknown"


class KayaListener:
    def __init__(self, on_event):
        self._on_event   = on_event
        self._lock       = Lock()
        self._event_count = 0
        self._modifiers  = 0
        self._is_running = False
        self._held_keys  = set()
        self._cached_app_name      = "unknown"
        self._app_name_update_count = 0

    def start(self):
        print("[LISTENER] Starting global keyboard listener...", flush=True)
        try:
            self._try_pynput()
            return
        except Exception as e:
            print(f"[LISTENER] pynput failed: {e}", flush=True)
        print("[LISTENER] Keyboard listener unavailable, using fallback mode.", flush=True)

    def _try_pynput(self):
        from pynput import keyboard

        def on_press(key):
            try:
                keycode      = 0
                is_backspace = False
                char         = None
                key_id       = str(key)

                if hasattr(key, 'char') and key.char is not None:
                    char   = key.char
                    keycode = ord(char) if len(char) == 1 else 0
                    key_id  = char
                elif key == keyboard.Key.backspace:
                    is_backspace = True
                    keycode = 8
                    key_id  = 'backspace'
                elif key == keyboard.Key.space:
                    char   = ' '
                    keycode = 32
                    key_id  = 'space'
                elif key == keyboard.Key.enter:
                    char   = '\n'
                    keycode = 13
                    key_id  = 'enter'
                elif key == keyboard.Key.tab:
                    char   = '\t'
                    keycode = 9
                    key_id  = 'tab'
                elif key == keyboard.Key.left:
                    keycode = 37
                    key_id  = 'left'
                elif key == keyboard.Key.right:
                    keycode = 39
                    key_id  = 'right'
                elif key == keyboard.Key.down:
                    keycode = 40
                    key_id  = 'down'
                elif key == keyboard.Key.up:
                    keycode = 38
                    key_id  = 'up'

                if keycode > 0 or is_backspace:
                    with self._lock:
                        if key_id not in self._held_keys:
                            self._held_keys.add(key_id)
                            self._event_count += 1
                            self._app_name_update_count += 1
                            if self._app_name_update_count >= 10:
                                self._cached_app_name = get_active_window_name()
                                self._app_name_update_count = 0
                            if is_backspace:
                                print(f"[{self._event_count}] BACKSPACE", flush=True)
                            elif char:
                                print(f"[{self._event_count}] '{char}'", flush=True)
                            else:
                                print(f"[{self._event_count}] key {keycode}", flush=True)
                            payload = {
                                "ts":           time.time(),
                                "is_down":      True,
                                "keycode":      keycode,
                                "is_backspace": is_backspace,
                                "char":         char,
                                "app_name":     self._cached_app_name,
                                "modifiers":    self._modifiers,
                            }
                            self._on_event(payload)
            except Exception:
                pass

        def on_release(key):
            try:
                key_id = str(key)
                if hasattr(key, 'char') and key.char is not None:
                    key_id = key.char
                elif key == keyboard.Key.backspace:
                    key_id = 'backspace'
                elif key == keyboard.Key.space:
                    key_id = 'space'
                elif key == keyboard.Key.enter:
                    key_id = 'enter'
                elif key == keyboard.Key.tab:
                    key_id = 'tab'
                elif key == keyboard.Key.left:
                    key_id = 'left'
                elif key == keyboard.Key.right:
                    key_id = 'right'
                elif key == keyboard.Key.down:
                    key_id = 'down'
                elif key == keyboard.Key.up:
                    key_id = 'up'
                with self._lock:
                    self._held_keys.discard(key_id)
            except Exception:
                pass

        listener = keyboard.Listener(on_press=on_press, on_release=on_release)
        listener.start()
        self._is_running = True
        print("[LISTENER] ✓ Keyboard monitor started via pynput", flush=True)

    def stop(self):
        self._is_running = False
        print(f"[LISTENER] Keyboard monitor stopped. Total events: {self._event_count}", flush=True)
