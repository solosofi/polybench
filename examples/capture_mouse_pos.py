import time

import pyautogui


def main():
    print("Move your mouse to a UI element. Press Ctrl+C to stop.")
    try:
        while True:
            x, y = pyautogui.position()
            print(f"\r{x},{y}   ", end="")
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nDone.")


if __name__ == "__main__":
    main()
