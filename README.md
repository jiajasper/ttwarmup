# macOS Auto Clicker

A powerful automation tool for macOS that allows you to record and replay mouse clicks and swipes with randomized timing and order.

## Features

- Record and name mouse clicks and swipes
- Build sequences of actions
- Randomize action order per loop
- Random delay between actions (1-5 seconds)
- Save and load configurations
- Global ESC hotkey to stop automation
- Simple and intuitive GUI

## Installation

1. Install Python 3.10 or higher if you haven't already
2. Install required packages:
   ```bash
   pip install pyautogui keyboard
   ```
3. Enable accessibility permissions:
   - Open System Settings
   - Go to Privacy & Security > Accessibility
   - Click the lock icon to make changes
   - Add Terminal or Python to the list of allowed apps

## Usage

1. Run the script:
   ```bash
   python main.py
   ```

2. Using the GUI:
   - Click "Record Click" to save a mouse position
   - Click "Record Swipe" to save a swipe gesture
   - Add recorded actions to your sequence
   - Click "Start" to begin automation
   - Press ESC at any time to stop

3. Configuration:
   - All settings are saved in `clicker_config.json`
   - The file is automatically created and updated

## Requirements

- macOS
- Python 3.10+
- pyautogui
- keyboard
- tkinter (built-in)

## Security Note

The keyboard module requires sudo privileges on macOS. This is necessary for the ESC hotkey functionality to work properly.

## License

MIT License 