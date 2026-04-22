#!/usr/bin/env python3
"""
Global keyboard capture daemon.
Runs as a background service and sends keyboard events to the main app.
"""

import time
import requests
import sys

def main():
    try:
        from pynput import keyboard
        print("[DAEMON] pynput imported successfully")
    except ImportError:
        print("[DAEMON] ERROR: pynput not available")
        sys.exit(1)

    PORT = 9876
    server_url = f"http://127.0.0.1:{PORT}"
    last_send = 0

    def on_press(key):
        nonlocal last_send
        try:
            char = None
            if hasattr(key, 'char') and key.char:
                char = key.char
            elif key == keyboard.Key.space:
                char = ' '
            elif key == keyboard.Key.backspace:
                char = 'backspace'
            elif key == keyboard.Key.enter:
                char = '\n'
            elif key == keyboard.Key.tab:
                char = '\t'

            if char:
                try:
                    requests.get(f"{server_url}/inject-event?char={char}", timeout=0.1)
                    print(f"[DAEMON] Sent: {repr(char)}")
                except:
                    pass
        except:
            pass

    print("[DAEMON] Starting global keyboard listener...")
    listener = keyboard.Listener(on_press=on_press)
    listener.start()
    print("[DAEMON] Listener started. Waiting for keyboard input...")
    print("[DAEMON] Press Ctrl+C to stop")

    try:
        listener.join()
    except KeyboardInterrupt:
        print("[DAEMON] Shutting down...")
        listener.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()
