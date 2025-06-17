import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import random
import time
import threading
import pyautogui
from pynput import mouse, keyboard
from typing import Dict, List, Tuple, Optional

class AutoClicker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Auto Clicker")
        self.root.geometry("800x600")
        
        self.config_file = "clicker_config.json"
        self.config = self.load_config()
        self.is_running = False
        self.thread = None
        self.esc_pressed = False
        
        self.recording_action = None
        self.mouse_listener = None

        # Setup keyboard listener for stopping automation
        self.keyboard_listener = keyboard.Listener(on_press=self.on_press)
        self.keyboard_listener.start()
        
        self.setup_gui()
        self.update_action_labels()
        self.update_coordinates()
        
    def on_press(self, key):
        try:
            if key == keyboard.Key.esc or key == keyboard.KeyCode.from_char('q'):
                if self.is_running:
                    self.esc_pressed = True
                    self.stop_automation()
                elif self.mouse_listener and self.mouse_listener.is_alive():
                    self.cancel_recording()
        except AttributeError:
            pass
    
    def on_click(self, x, y, button, pressed):
        # We only care about the press, not the release
        if not pressed:
            return

        pos = (x, y)
        # Ignore clicks inside the application window
        if self.is_click_in_app(pos):
            return

        if self.recording_action:
            self.save_recorded_action(pos)
        
        # Stop the listener by returning False
        return False

    def cancel_recording(self):
        if self.mouse_listener and self.mouse_listener.is_alive():
            self.mouse_listener.stop()
        self.recording_action = None
        self.toggle_widget_state("normal")
        self.update_status(message="Recording canceled.")

    def save_recorded_action(self, pos):
        action = self.recording_action
        if action in ["like", "bookmark", "follow"]:
            self.config["actions"][action] = {"type": "click", "pos": [pos[0], pos[1]]}
        
        self.save_config()
        self.update_action_labels()
        self.toggle_widget_state("normal")
        self.update_status(message=f"Recorded '{action}' at {pos}")
        self.recording_action = None

    def load_config(self) -> dict:
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                if "actions" not in config:
                    # Invalidate old config format
                    raise ValueError("Old config format")
                return config
            except (json.JSONDecodeError, ValueError):
                # Config is invalid or old, create a new one
                return self.get_default_config(and_save=True)
        # Config file doesn't exist, create a new one
        return self.get_default_config(and_save=True)
    
    def get_default_config(self, and_save=False) -> dict:
        config = {
            "actions": {
                "like": None,
                "bookmark": None,
                "follow": None,
                "swipe_up": {
                    "type": "scroll",
                    "amount": -200000,  # Scrolls Up (3x scale)
                    "direction": "vertical"
                },
                "swipe_down": {
                    "type": "scroll",
                    "amount": 200000,  # Scrolls Down (3x scale)
                    "direction": "vertical"
                }
            },
            "sequence": [],
            "settings": {
                "random_order": True,
                "random_delay": True,
                "delay_range": [1, 5]
            }
        }
        if and_save:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        return config
    
    def save_config(self):
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=2)
    
    def setup_gui(self):
        self.root.bind("<Configure>", self.on_window_move)
        
        # Create main frames
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill="x", padx=10, pady=5)
        
        self.coord_label = ttk.Label(top_frame, text="Mouse: X: 0, Y: 0")
        self.coord_label.pack(side="left")
        
        status_frame = ttk.LabelFrame(self.root, text="Status", padding="5")
        status_frame.pack(fill="x", padx=10, pady=5)
        self.status_label = ttk.Label(status_frame, text="Status: Ready")
        self.status_label.pack(fill="x", padx=5, pady=5)
        
        recording_frame = ttk.LabelFrame(self.root, text="Record Actions", padding="10")
        recording_frame.pack(fill="x", padx=10, pady=5)
        
        self.record_buttons = {}
        self.action_labels = {}

        actions = ["like", "bookmark", "follow", "swipe_up", "swipe_down"]
        for action in actions:
            frame = ttk.Frame(recording_frame)
            frame.pack(fill="x", pady=4)
            
            label_text = f"{action.replace('_', ' ').title()}:"
            ttk.Label(frame, text=label_text, width=15).pack(side="left")
            
            self.action_labels[action] = ttk.Label(frame, text="Not Recorded", width=25)
            self.action_labels[action].pack(side="left", padx=5)

            if "swipe" not in action:
                cmd = lambda a=action: self.start_click_recording(a)
                self.record_buttons[action] = ttk.Button(frame, text="Record", command=cmd)
                self.record_buttons[action].pack(side="left", padx=5)
        
        control_frame = ttk.Frame(self.root)
        control_frame.pack(fill="x", padx=10, pady=10)
        
        self.generate_seq_button = ttk.Button(control_frame, text="Generate Sequence", command=self.generate_sequence)
        self.generate_seq_button.pack(side="left", padx=5)
        
        self.start_button = ttk.Button(control_frame, text="Start", command=self.start_automation)
        self.start_button.pack(side="left", padx=5)
        
        self.stop_button = ttk.Button(control_frame, text="Stop", command=self.stop_automation, state="disabled")
        self.stop_button.pack(side="left", padx=5)
        
        sequence_frame = ttk.LabelFrame(self.root, text="Current Sequence", padding="10")
        sequence_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.sequence_list = ttk.Treeview(sequence_frame, columns=("Action", "Details"), show="headings")
        self.sequence_list.heading("Action", text="Action")
        self.sequence_list.heading("Details", text="Details")
        self.sequence_list.pack(fill="both", expand=True)
        
        self.update_sequence_list()

    def on_window_move(self, event):
        # This is a bit of a hack to ensure the window geometry is updated
        # before we check click positions.
        self.root.update_idletasks()

    def start_click_recording(self, action):
        if self.mouse_listener and self.mouse_listener.is_alive():
            messagebox.showwarning("Recording in Progress", "Another recording is already in progress.")
            return

        self.recording_action = action
        self.toggle_widget_state("disabled")
        
        self.update_status(message=f"Recording '{action}': Click the target location. (Press ESC to cancel)")
        
        # Start a new listener in a separate thread
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.mouse_listener.start()

    def record_scroll_action(self, action):
        # For a "swipe up" on a feed, we want to scroll down.
        # On macOS with natural scrolling, a positive value scrolls down.
        # We use a larger value to make it more noticeable.
        amount = 500 if action == "swipe_up" else -500
        self.config["actions"][action] = {
            "type": "scroll",
            "amount": amount,
            "direction": "vertical"
        }
        self.save_config()
        self.update_action_labels()
        self.update_status(message=f"Recorded '{action}'.")

    def update_action_labels(self):
        for action, data in self.config["actions"].items():
            if data:
                if data["type"] == "click":
                    pos = data["pos"]
                    text = f"Click at ({pos[0]}, {pos[1]})"
                else:
                    direction = "Down" if data['amount'] > 0 else "Up"
                    text = f"Scroll {direction}"
                self.action_labels[action].config(text=text)
            else:
                self.action_labels[action].config(text="Not Recorded")

    def toggle_widget_state(self, state):
        for button in self.record_buttons.values():
            button.config(state=state)
        self.generate_seq_button.config(state=state)
        self.start_button.config(state=state)
        # Stop button is handled separately
    
    def is_click_in_app(self, pos):
        x, y = self.root.winfo_x(), self.root.winfo_y()
        width, height = self.root.winfo_width(), self.root.winfo_height()
        return (x <= pos[0] <= x + width and y <= pos[1] <= y + height)
    
    def generate_sequence(self):
        missing = [a for a, d in self.config["actions"].items() if d is None]
        if missing:
            messagebox.showwarning("Missing Actions", 
                f"Please record all actions first. Missing: {', '.join(missing)}")
            return
        
        # Define weights for each action
        weights = {
            "swipe_up": 5,     # 5% of actions
            "like": 15,        # 30% of actions
            "bookmark": 5,    # 10% of actions
            "follow": 5,       # 5% of actions
            "swipe_down": 90   # 50% of actions
        }
        
        total_steps = 100
        seq = []
        
        # First, create pools of actions based on weights
        action_pools = {}
        for action, weight in weights.items():
            count = int((weight / 100) * total_steps)
            action_pools[action] = [action] * count
        
        # Combine all actions into a single pool
        all_actions = []
        for actions in action_pools.values():
            all_actions.extend(actions)
        
        # Shuffle the actions
        random.shuffle(all_actions)
        
        # Build sequence ensuring no consecutive likes
        while all_actions:
            if not seq:  # First action
                seq.append({
                    "type": self.config["actions"][all_actions[0]]["type"],
                    "name": all_actions.pop(0)
                })
            else:
                # Find next valid action
                valid_action = None
                for i, action in enumerate(all_actions):
                    if action != "like" or seq[-1]["name"] != "like":
                        valid_action = action
                        all_actions.pop(i)
                        break
                
                if valid_action is None:
                    # If no valid action found, add a swipe action
                    valid_action = "swipe_down" if random.random() < 0.5 else "swipe_up"
                
                seq.append({
                    "type": self.config["actions"][valid_action]["type"],
                    "name": valid_action
                })
        
        # If we have less than 100 steps due to rounding, add more swipe actions
        while len(seq) < total_steps:
            action = "swipe_down" if random.random() < 0.5 else "swipe_up"
            seq.append({
                "type": self.config["actions"][action]["type"],
                "name": action
            })
        
        self.config["sequence"] = seq
        self.save_config()
        self.update_sequence_list()
        messagebox.showinfo("Success", f"Generated sequence with {len(seq)} steps!")
    
    def update_sequence_list(self):
        for item in self.sequence_list.get_children():
            self.sequence_list.delete(item)
        
        for action in self.config["sequence"]:
            name = action["name"]
            data = self.config["actions"][name]
            details = ""
            if data["type"] == "click":
                pos = data["pos"]
                details = f"Click at ({pos[0]}, {pos[1]})"
            else:
                details = f"Scroll {abs(data['amount'])}px {'Up' if data['amount'] < 0 else 'Down'}"
            
            self.sequence_list.insert("", "end", values=(
                name.replace("_", " ").title(), details
            ))
    
    def update_coordinates(self):
        pos = pyautogui.position()
        self.coord_label.config(text=f"Mouse: X: {pos.x}, Y: {pos.y}")
        self.root.after(100, self.update_coordinates)
    
    def update_status(self, next_action=None, countdown=None, message=None):
        if message:
            status_text = message
        elif self.is_running:
            status_text = f"Status: Running\n"
            if next_action:
                name = next_action['name'].replace('_', ' ').title()
                status_text += f"Next Action: {name}\n"
            if countdown is not None and countdown > 0:
                status_text += f"Countdown to next action: {countdown:.1f}s"
            else:
                status_text += "Executing action..."
        else:
             status_text = "Status: Ready"

        self.status_label.config(text=status_text)
        self.root.update_idletasks()
    
    def execute_action(self, action):
        action_details = self.config["actions"][action["name"]]
        if action["type"] == "click":
            pos = action_details["pos"]
            pyautogui.click(pos[0], pos[1])
        elif action["type"] == "scroll":
            # Perform 3 fast consecutive scrolls
            for _ in range(3):
                pyautogui.scroll(action_details["amount"] // 3)  # Divide the amount by 3
                time.sleep(0.05)  # Small delay between scrolls
    
    def automation_loop(self):
        # 3-second countdown before starting
        for i in range(3, 0, -1):
            if self.esc_pressed: break
            self.update_status(message=f"Starting in {i}...")
            time.sleep(1)
        
        while self.is_running and not self.esc_pressed:
            sequence = self.config["sequence"].copy()
            if self.config["settings"]["random_order"]:
                random.shuffle(sequence)
                
            for action in sequence:
                if not self.is_running or self.esc_pressed: break
                
                self.update_status(next_action=action)
                self.execute_action(action)
                
                delay = random.uniform(
                    self.config["settings"]["delay_range"][0],
                    self.config["settings"]["delay_range"][1]
                )
                start_time = time.time()
                while time.time() - start_time < delay:
                    if not self.is_running or self.esc_pressed: break
                    remaining = delay - (time.time() - start_time)
                    self.update_status(next_action=action, countdown=remaining)
                    time.sleep(0.1)
            if self.esc_pressed: break
        
        # Cleanup after loop ends
        self.is_running = False
        self.esc_pressed = False
        self.toggle_widget_state("normal")
        self.stop_button.config(state="disabled")
        self.update_status(message="Automation stopped.")
    
    def start_automation(self):
        if not self.config["sequence"]:
            messagebox.showwarning("No Sequence", "Please generate a sequence first!")
            return
            
        self.is_running = True
        self.esc_pressed = False
        
        self.toggle_widget_state("disabled")
        self.stop_button.config(state="normal")
        
        self.thread = threading.Thread(target=self.automation_loop, daemon=True)
        self.thread.start()
    
    def stop_automation(self):
        if self.is_running:
            self.esc_pressed = True # Signal the loop to stop
        # The loop itself will handle UI updates and state changes
    
    def run(self):
        self.root.mainloop()
        self.keyboard_listener.stop()

if __name__ == "__main__":
    app = AutoClicker()
    app.run() 