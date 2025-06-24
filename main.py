import sys
import os
import json
import random
import time
import threading
from PyQt6.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget, QLabel,
                             QGridLayout, QGroupBox, QTextEdit, QMessageBox, QHBoxLayout)
from PyQt6.QtGui import QPixmap, QImage, QFont, QPainter, QPen, QPainterPath
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
import numpy as np
import pyautogui
from pynput import mouse, keyboard
from PIL import Image, ImageDraw
from PIL.ImageQt import ImageQt

# --- Accessibility permission check for macOS ---
def check_accessibility_permission():
    import platform
    if platform.system() != "Darwin":
        return True  # Only check on macOS
    try:
        current_pos = pyautogui.position()
        pyautogui.moveTo(current_pos[0], current_pos[1], duration=0.1)
        return True
    except Exception:
        return False

class CountdownLabel(QLabel):
    """A custom label for displaying a countdown on the cursor."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFont(QFont("Arial", 64, QFont.Weight.Bold))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(100, 100)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        path = QPainterPath()
        path.addText(self.rect().center().x() - 40, self.rect().center().y() + 25, self.font(), self.text())
        
        # Draw outline
        pen = QPen(Qt.GlobalColor.black, 4)
        painter.setPen(pen)
        painter.drawPath(path)
        
        # Draw fill
        painter.setPen(Qt.GlobalColor.white)
        painter.fillPath(path, Qt.GlobalColor.white)

# Worker signals must be a QObject
class WorkerSignals(QObject):
    update_status = pyqtSignal(str)
    automation_finished = pyqtSignal()
    cancel_recording_signal = pyqtSignal()
    highlight_sequence_step = pyqtSignal(int)

class SkeuomorphicWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Core application logic initialization
        self.config_file = "clicker_config.json"
        self.config = self.load_config()
        self.is_running = False
        self.thread = None
        self.esc_pressed = False
        self.recording_action = None
        self.countdown_label = None # For the on-cursor countdown
        
        # Setup keyboard listener for stopping automation
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press, daemon=True)
        self.keyboard_listener.start()

        self.signals = WorkerSignals()
        self.signals.update_status.connect(self.update_status_label)
        self.signals.automation_finished.connect(self.on_automation_finished)
        self.signals.cancel_recording_signal.connect(self.cancel_recording)
        self.signals.highlight_sequence_step.connect(self.update_sequence_list)

        self.setWindowTitle("TT Warmup Auto")
        self.setGeometry(100, 100, 800, 750)

        self.setup_ui()
        self.update_action_labels()
        self.update_sequence_list()
    
    def setup_ui(self):
        # Background
        self.background_label = QLabel(self)
        self.create_gradient_noise_background()

        # Main widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # Style for group boxes
        group_box_style = """
            QGroupBox {
                background-color: rgba(240, 240, 240, 0.85);
                border: 1px solid rgba(200, 200, 200, 0.85);
                border-radius: 15px;
                margin-top: 1em;
                font-size: 14px;
                font-weight: bold;
                color: black;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 5px 10px;
            }
            QGroupBox QLabel {
                color: black;
                font-weight: normal;
                background: transparent;
            }
        """

        gray_button_style = """
            QPushButton {
                color: black; border: 1px solid #999; border-radius: 6px;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #f6f7fa, stop: 1 #dadbde);
                padding: 8px; font-size: 12px; font-weight: bold;
            }
            QPushButton:pressed { background-color: #dadbde; }
            QPushButton:disabled { color: #888; background-color: #ccc; }
        """
        blue_button_style = """
            QPushButton {
                color: black; border: 1px solid #2d73a0; border-radius: 6px;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #8cbbe0, stop: 1 #5d9ecf);
                padding: 8px; font-size: 12px; font-weight: bold;
            }
            QPushButton:pressed { background-color: #5d9ecf; }
        """
        red_button_style = """
            QPushButton {
                color: white; border: 1px solid #b02a2a; border-radius: 6px;
                background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #f48080, stop: 1 #e04040);
                padding: 8px; font-size: 12px; font-weight: bold;
            }
            QPushButton:pressed { background-color: #e04040; }
        """
        
        # --- Top info bar (coordinates + status) ---
        self.top_info_widget = QWidget()
        top_info_layout = QHBoxLayout(self.top_info_widget)
        self.coord_label = QLabel("Mouse: X: 0, Y: 0")
        self.coord_label.setFont(QFont("Georgia", 14))
        self.coord_label.setStyleSheet("color: black; background: transparent;")
        self.status_label = QLabel("Status: Ready")
        self.status_label.setFont(QFont("Georgia", 12))
        self.status_label.setStyleSheet("color: black; background: transparent;")
        top_info_layout.addWidget(self.coord_label, alignment=Qt.AlignmentFlag.AlignLeft)
        top_info_layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignRight)
        main_layout.addWidget(self.top_info_widget)

        # Timer to update mouse coordinates
        self.coord_timer = QTimer(self)
        self.coord_timer.setInterval(100)
        self.coord_timer.timeout.connect(self.update_coordinates)
        self.coord_timer.start()

        # --- Recording Box ---
        self.recording_box = QGroupBox("Record Actions")
        self.recording_box.setStyleSheet(group_box_style)
        recording_layout = QGridLayout(self.recording_box)
        
        self.record_buttons = {}
        self.action_labels = {}
        actions = ["like", "bookmark", "follow"]
        for i, action in enumerate(actions):
            label_text = f"{action.replace('_', ' ').title()}:"
            recording_layout.addWidget(QLabel(label_text), i, 0)
            
            self.action_labels[action] = QLabel("Not Recorded")
            recording_layout.addWidget(self.action_labels[action], i, 1)

            button = QPushButton("Record Mouse Click Location")
            button.setStyleSheet(gray_button_style)
            button.clicked.connect(lambda _, a=action: self.start_click_recording(a))
            self.record_buttons[action] = button
            recording_layout.addWidget(button, i, 2)
        main_layout.addWidget(self.recording_box)

        # --- Controls Box ---
        self.controls_widget = QWidget()
        controls_layout = QHBoxLayout(self.controls_widget)
        self.generate_seq_button = QPushButton("Generate Sequence")
        self.generate_seq_button.setStyleSheet(gray_button_style)
        self.generate_seq_button.clicked.connect(self.generate_sequence)
        self.start_button = QPushButton("Start")
        self.start_button.setStyleSheet(blue_button_style)
        self.start_button.clicked.connect(self.start_automation)
        controls_layout.addWidget(self.generate_seq_button)
        controls_layout.addWidget(self.start_button)
        main_layout.addWidget(self.controls_widget)
        
        # --- Sequence Box ---
        self.sequence_box = QGroupBox("Current Sequence")
        self.sequence_box.setStyleSheet(group_box_style)
        sequence_layout = QVBoxLayout(self.sequence_box)
        self.sequence_text = QTextEdit()
        self.sequence_text.setReadOnly(True)
        self.sequence_text.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.85);
            border-radius: 10px;
            color: black;
            font-size: 12px;
        """)
        sequence_layout.addWidget(self.sequence_text)
        main_layout.addWidget(self.sequence_box)

        # --- Stop Button (fixed position, always in main layout) ---
        self.stop_button = QPushButton("Stop")
        self.stop_button.setStyleSheet(red_button_style)
        self.stop_button.clicked.connect(self.stop_automation)
        self.stop_button.setVisible(False)
        main_layout.addWidget(self.stop_button)

        self.show_setup_view() # Set initial UI state

    def on_press(self, key):
        try:
            if key == keyboard.Key.esc or key == keyboard.KeyCode.from_char('q'):
                if self.is_running:
                    self.esc_pressed = True
                    self.stop_automation()
                elif self.recording_action is not None:
                    # Emit signal to safely interact with GUI from listener thread
                    self.signals.cancel_recording_signal.emit()
        except AttributeError:
            pass

    def cancel_recording(self):
        if hasattr(self, 'record_timer') and self.record_timer.isActive():
            self.record_timer.stop()
        if hasattr(self, 'position_timer') and self.position_timer.isActive():
            self.position_timer.stop()
        if self.countdown_label:
            self.countdown_label.hide()
            
        self.recording_action = None
        self.toggle_widget_state(True)
        self.update_status_label("Recording canceled.")

    def save_recorded_action(self, action, pos):
        if action in ["like", "bookmark", "follow"]:
            self.config["actions"][action] = {"type": "click", "pos": [pos[0], pos[1]]}
        self.save_config()
        self.update_action_labels()
        
    def start_click_recording(self, action):
        if self.recording_action is not None:
            QMessageBox.warning(self, "Recording in Progress", "Another recording is already in progress.")
            return
        self.recording_action = action
        self.toggle_widget_state(False)
        self.countdown = 3
        self.update_status_label(f"Move your mouse to the target location. Recording in {self.countdown}s...")
        if not self.countdown_label:
            self.countdown_label = CountdownLabel()
        self.countdown_label.setText(str(self.countdown))
        self.countdown_label.show()
        self.record_timer = QTimer(self)
        self.record_timer.setInterval(1000)
        self.record_timer.timeout.connect(self.record_countdown_tick)
        self.record_timer.start()
        self.position_timer = QTimer(self)
        self.position_timer.setInterval(16)
        self.position_timer.timeout.connect(self.update_cursor_widget_position)
        self.position_timer.start()

    def record_countdown_tick(self):
        self.countdown -= 1
        self.countdown_label.setText(str(self.countdown))
        
        if self.countdown <= 0:
            self.record_timer.stop()
            self.position_timer.stop()
            self.countdown_label.hide()
            pos = pyautogui.position()
            self.finalize_recording(self.recording_action, (pos.x, pos.y))

    def update_cursor_widget_position(self):
        if self.countdown_label:
            pos = pyautogui.position()
            # Center the label on the cursor
            self.countdown_label.move(pos.x - self.countdown_label.width() // 2, pos.y - self.countdown_label.height() // 2)

    def finalize_recording(self, action, pos):
        self.save_recorded_action(action, pos)
        self.recording_action = None
        self.toggle_widget_state(True)
        self.update_status_label(f"Recorded '{action}' at {pos}")

    def load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return self.get_default_config(and_save=True)
        return self.get_default_config(and_save=True)
    
    def get_default_config(self, and_save=False) -> dict:
        config = {
            "actions": {"like": None, "bookmark": None, "follow": None,
                "swipe_up": {"type": "scroll", "amount": -200000},
                "swipe_down": {"type": "scroll", "amount": 200000}},
            "sequence": [],
            "settings": {"random_order": True, "random_delay": True, "delay_range": [1, 5]}
        }
        if and_save: self.save_config(config)
        return config
    
    def save_config(self, config_data=None):
        with open(self.config_file, 'w') as f:
            json.dump(config_data if config_data else self.config, f, indent=2)

    def update_action_labels(self):
        for action, data in self.config["actions"].items():
            if action in self.action_labels:
                if data and data["type"] == "click":
                    pos = data["pos"]
                    text = f"Click at ({pos[0]}, {pos[1]})"
                    self.action_labels[action].setText(text)
                else:
                    self.action_labels[action].setText("Not Recorded")

    def toggle_widget_state(self, enabled):
        for button in self.record_buttons.values():
            button.setEnabled(enabled)
        self.generate_seq_button.setEnabled(enabled)
        self.start_button.setEnabled(enabled)
        self.stop_button.setEnabled(not enabled)

    def generate_sequence(self):
        # Weighted random sequence generator
        actions = [a for a, d in self.config["actions"].items() if d is not None]
        if len(actions) < 5:
            QMessageBox.warning(self, "Missing Actions", "Please record all actions first.")
            return

        # Define weights for each action
        weights_map = {
            "swipe_down": 10,   
            "swipe_up": 80,    
            "like": 5,
            "bookmark": 3,
            "follow": 2
        }
        # Only include actions that are recorded
        weights = [weights_map.get(a, 1) for a in actions]

        seq = []
        for _ in range(100):
            action_name = random.choices(actions, weights=weights, k=1)[0]
            action_type = self.config["actions"][action_name]["type"]
            seq.append({"type": action_type, "name": action_name})

        self.config["sequence"] = seq
        self.save_config()
        self.update_sequence_list()
        QMessageBox.information(self, "Success", f"Generated sequence with {len(seq)} steps!")

    def update_sequence_list(self, highlight_index=None):
        self.sequence_text.clear()
        html = ""
        for idx, action in enumerate(self.config["sequence"]):
            name = action["name"].replace("_", " ").title()
            if highlight_index is not None and idx == highlight_index:
                html += f'<div style="background-color:#cce6ff;padding:2px 4px;border-radius:4px;">→ {name}</div>'
            else:
                html += f'<div>{name}</div>'
        self.sequence_text.setHtml(html)

    def update_coordinates(self):
        pos = pyautogui.position()
        self.coord_label.setText(f"Mouse: X: {pos.x}, Y: {pos.y}")
        
    def update_status_label(self, message):
        self.status_label.setText(message)

    def execute_action(self, action):
        action_details = self.config["actions"][action["name"]]
        if action["type"] == "click":
            pos = action_details["pos"]
            pyautogui.click(pos[0], pos[1])
        elif action["type"] == "scroll":
            pyautogui.scroll(action_details["amount"])

    def automation_loop(self):
        for i in range(3, 0, -1):
            if self.esc_pressed: break
            self.signals.update_status.emit(f"Starting in {i}...")
            time.sleep(1)
        
        sequence = self.config["sequence"].copy()
        while self.is_running and not self.esc_pressed:
            if self.config["settings"]["random_order"]:
                random.shuffle(sequence)
            
            for idx, action in enumerate(sequence):
                if not self.is_running or self.esc_pressed: break
                name = action['name'].replace('_', ' ').title()
                self.signals.update_status.emit(f"Executing: {name}")
                # Highlight current step via signal
                self.signals.highlight_sequence_step.emit(idx)
                self.execute_action(action)
                delay = random.uniform(*self.config["settings"]["delay_range"])
                start_time = time.time()
                while time.time() - start_time < delay:
                    if not self.is_running or self.esc_pressed: break
                    remaining = delay - (time.time() - start_time)
                    self.signals.update_status.emit(f"Next action in {remaining:.1f}s")
                    time.sleep(0.1)
            if self.esc_pressed: break
        # Remove highlight at end
        self.signals.highlight_sequence_step.emit(-1)
        self.signals.automation_finished.emit()
    
    def start_automation(self):
        if not self.config["sequence"]:
            QMessageBox.warning(self, "No Sequence", "Please generate a sequence first!")
            return
        self.is_running = True
        self.esc_pressed = False
        self.show_automation_view()
        self.thread = threading.Thread(target=self.automation_loop, daemon=True)
        self.thread.start()
    
    def stop_automation(self):
        if self.is_running:
            self.esc_pressed = True

    def on_automation_finished(self):
        self.is_running = False
        self.esc_pressed = False
        self.show_setup_view()
        self.update_status_label("Automation stopped.")

    def create_gradient_noise_background(self):
        width, height = self.size().width(), self.size().height()
        if width == 0 or height == 0: return

        gradient = Image.new('RGB', (width, height))
        draw = ImageDraw.Draw(gradient)
        for y in range(height):
            ratio = y / height
            r = int(245 * (1 - ratio) + 235 * ratio)
            g = int(240 * (1 - ratio) + 230 * ratio)
            b = int(235 * (1 - ratio) + 225 * ratio)
            draw.line([(0, y), (width, y)], fill=(r, g, b))

        noise = np.random.normal(0, 4, (height, width, 3)).astype(np.uint8)
        noise_img = Image.fromarray(noise)
        background_img = Image.blend(gradient, noise_img, 0.03)

        qimage = ImageQt(background_img)
        pixmap = QPixmap.fromImage(qimage)
        self.background_label.setPixmap(pixmap)
        self.background_label.setGeometry(0, 0, width, height)
        self.background_label.lower()

    def resizeEvent(self, event):
        self.create_gradient_noise_background()
        super().resizeEvent(event)
    
    def closeEvent(self, event):
        self.keyboard_listener.stop()
        event.accept()

    def show_setup_view(self):
        self.top_info_widget.show()
        self.recording_box.show()
        self.controls_widget.show()
        self.sequence_box.show()
        self.generate_seq_button.show()
        self.start_button.show()
        self.stop_button.setVisible(False)

    def show_automation_view(self):
        self.top_info_widget.hide()
        self.recording_box.hide()
        self.controls_widget.hide()
        self.sequence_box.show()
        self.stop_button.setVisible(True)

if __name__ == "__main__":
    # Check for Accessibility permission on macOS
    if not check_accessibility_permission():
        from PyQt6.QtWidgets import QApplication, QMessageBox
        import subprocess
        app = QApplication(sys.argv)
        QMessageBox.critical(
            None,
            "Accessibility Permission Required",
            "Please grant Accessibility permissions to your Terminal or Python app in System Settings > Privacy & Security > Accessibility.\n\nThe Accessibility settings will now open. After granting permission, restart the app."
        )
        # Open Accessibility settings
        subprocess.run(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
        sys.exit(1)
    app = QApplication(sys.argv)
    window = SkeuomorphicWindow()
    window.show()
    sys.exit(app.exec()) 