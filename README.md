# TT Warmup Auto

A very simple automation tool for recording and replaying mouse actions. Works on macOS, Windows, and Linux.

## Features

- Record mouse positions for Like, Bookmark, and Follow actions (no click needed, just move the cursor!)
- Build and randomize sequences of actions
- Adjustable random delay between actions
- Glassmorphic, modern UI with clear status and sequence highlighting
- On-cursor countdown for easy recording
- Cross-platform launchers for easy use (no Python knowledge required)
- ESC or Stop button to halt automation at any time

## TikTok Warmup Use Case

This tool is perfect for automating engagement actions (like, bookmark, follow) on TikTok, especially for warmup or botting scenarios. Here's how to use it for TikTok:

1. **Start Screen Mirroring or Open TikTok Web**
   - If you're using an iPhone, start a screen mirroring session to your computer (e.g., using QuickTime or a mirroring app).
   - Or, simply open TikTok in your web browser.

2. **Launch TT Warmup Auto**
   - Start the app using the launcher or from the terminal.

3. **Record Mouse Locations**
   - For each action (Like, Bookmark, Follow), click the corresponding "Record Mouse Click Location" button.
   - Move your mouse to the correct button on the mirrored TikTok screen or web page before the countdown ends. No need to click!
   - The app will save the coordinates for each action.

4. **Swipe Up/Down**
   - You do NOT need to configure swipe up or down. The tool is focused on engagement actions only.

5. **Edit Action Weights (Advanced)**
   - If you want to change how often each action appears in the generated sequence, you can edit the weights in the code (look for the `generate_sequence` method in `main.py`).

## Installation & Setup

### 1. Requirements
- Python 3.8+
- pip (Python package manager)

### 2. Download/Clone the Repository
```
git clone https://github.com/yourusername/ttwarmup.git
cd ttwarmup
```

### 3. Install Dependencies
You can do this manually:
```
pip install -r requirements.txt
```
Or just use the provided launcher (see below) and it will auto-install dependencies for you!

### 4. Initial Setup
The app will automatically create a `clicker_config.json` file when you first run it. If you want to start fresh, you can copy the template:
```
cp clicker_config_template.json clicker_config.json
```

## How to Launch the App

### On macOS/Linux
1. Double-click `Launch_TT_Warmup.command` in Finder or your file manager.
2. The first time, it will install dependencies, then launch the app.
3. The app will open in a Terminal window.

### On Windows
1. Double-click `Launch_TT_Warmup.bat` in File Explorer.
2. The first time, it will install dependencies, then launch the app.
3. The app will open in a Command Prompt window.

### For Developers: Run from Terminal
If you prefer to run the app directly from the command line (no launcher needed):

```
pip install -r requirements.txt
python main.py
```

- On Windows, you can use `python main.py`.
- On macOS/Linux, you can use `python3 main.py` if needed.

## How to Use

1. **Record Actions:**
   - Click a "Record Mouse Click Location" button for Like, Bookmark, or Follow.
   - Move your mouse to the target location before the countdown ends. No need to click!
   - The app will capture the cursor position automatically.

2. **Generate Sequence:**
   - Click "Generate Sequence" to create a randomized sequence of your actions.

3. **Start Automation:**
   - Click "Start". The UI will focus on the sequence and show only the Stop button.
   - The app will perform the actions in your sequence, with random delays.
   - The current step is highlighted in the sequence list.

4. **Stop Automation:**
   - Click the red "Stop" button or press ESC at any time to halt automation.

## Customization
- You can edit `requirements.txt` to add or update dependencies.
- The app saves its configuration in `clicker_config.json` in the same folder.
- Use `clicker_config_template.json` as a starting point for a fresh configuration.

## Troubleshooting
- If you see errors about missing modules, make sure Python and pip are installed and on your PATH.
- If you have issues with permissions, try running the launcher as administrator (Windows) or with `chmod +x` (macOS/Linux).

## License
MIT License 