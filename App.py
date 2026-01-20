import tkinter as tk
from tkinter import filedialog
import customtkinter as ctk
import keyboard
import pygame
import threading
import json
import os
import sys
import time

from Config import CONFIG_FILE, DEFAULT_CONFIG
from FlashOverlay import FlashOverlay

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

FIXED_IMAGE_NAME = "sheen.png"

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Spellblade Companion App")
        self.geometry("400x550") 
        self.resizable(False, False)

        self.config = self.load_config()
        self.is_running = False
        self.ping_timer = None
        self.last_update = 0 # For throttling the slider
        
        if "icon_scale" not in self.config:
            self.config["icon_scale"] = 1.0

        # --- UI LAYOUT ---
        ctk.CTkLabel(self, text="Settings", font=("Roboto", 20, "bold")).pack(pady=20)

        # 1. Trigger Keys
        frame_keys = ctk.CTkFrame(self)
        frame_keys.pack(pady=10, fill="x", padx=20)
        ctk.CTkLabel(frame_keys, text="Trigger Keys (Max 4):").pack(pady=5)
        
        row_inputs = ctk.CTkFrame(frame_keys, fg_color="transparent")
        row_inputs.pack(fill="x", padx=5, pady=5)
        
        self.key_entries = []
        current_keys = self.config.get("trigger_keys", [self.config.get("trigger_key", "F1")] + [""]*3)
        while len(current_keys) < 4: current_keys.append("")
        current_keys = current_keys[:4]

        for i in range(4):
            entry = ctk.CTkEntry(row_inputs, width=60, justify="center")
            entry.insert(0, current_keys[i])
            entry.pack(side="left", padx=5, expand=True)
            self.key_entries.append(entry)

        # 2. Sound File
        frame_sound = ctk.CTkFrame(self)
        frame_sound.pack(pady=10, fill="x", padx=20)
        self.btn_sound = ctk.CTkButton(frame_sound, text="Select Sound (WAV/MP3)", command=self.select_sound)
        self.btn_sound.pack(fill="x", padx=10, pady=5)
        self.lbl_sound = ctk.CTkLabel(frame_sound,
                                      text=os.path.basename(self.config["sound_file"]) or "No file selected",
                                      text_color="gray")
        self.lbl_sound.pack(pady=5)
        
        # 3. Size Slider
        frame_size = ctk.CTkFrame(self)
        frame_size.pack(pady=10, fill="x", padx=20)
        ctk.CTkLabel(frame_size, text="Icon Size:").pack(pady=5)
        
        self.slider_size = ctk.CTkSlider(frame_size, from_=0.2, to=3.0, command=self.update_size_realtime)
        self.slider_size.set(self.config["icon_scale"])
        self.slider_size.pack(fill="x", padx=20, pady=5)
        self.lbl_size_val = ctk.CTkLabel(frame_size, text=f"{int(self.config['icon_scale']*100)}%")
        self.lbl_size_val.pack(pady=2)

        # 4. Position Picker
        frame_pos = ctk.CTkFrame(self)
        frame_pos.pack(pady=10, fill="x", padx=20)
        self.btn_pos = ctk.CTkButton(frame_pos, text="Set Screen Position", fg_color="orange",
                                     command=self.pick_position)
        self.btn_pos.pack(fill="x", padx=10, pady=5)
        self.lbl_pos = ctk.CTkLabel(frame_pos, text=f"Current: X={self.config['pos_x']}, Y={self.config['pos_y']}")
        self.lbl_pos.pack(pady=5)

        # 5. Start/Stop
        self.btn_start = ctk.CTkButton(self, text="START LISTENER", fg_color="green", height=50,
                                       command=self.toggle_listener)
        self.btn_start.pack(pady=20, fill="x", padx=20)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.overlay = None
        self.refresh_overlay()

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except:
                return DEFAULT_CONFIG
        return DEFAULT_CONFIG

    def save_config(self):
        keys_to_save = [e.get().strip() for e in self.key_entries]
        self.config["trigger_keys"] = keys_to_save
        self.config["icon_scale"] = self.slider_size.get()
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def refresh_overlay(self):
        if self.overlay and self.overlay.root:
            self.overlay.root.destroy()
        
        img_path = resource_path(FIXED_IMAGE_NAME)
        scale = self.config.get("icon_scale", 1.0)
        
        self.overlay = FlashOverlay(img_path, scale)
        self.overlay.move_to(self.config["pos_x"], self.config["pos_y"])
        self.overlay.set_opacity(1.0)

    def update_size_realtime(self, value):
        # 1. Update text label (always feel responsive)
        self.lbl_size_val.configure(text=f"{int(value*100)}%")
        self.config["icon_scale"] = value

        # 2. THROTTLE: Only redraw the window max 30 times a second
        current_time = time.time()
        if current_time - self.last_update < 0.033: # 33ms = ~30fps
            return
        self.last_update = current_time

        # 3. Fast resize
        if self.overlay:
            self.overlay.resize_graphic(value)
            self.overlay.move_to(self.config["pos_x"], self.config["pos_y"])

    def select_sound(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3")])
        if path:
            self.config["sound_file"] = path
            self.lbl_sound.configure(text=os.path.basename(path))
            self.save_config()

    def pick_position(self):
        import ctypes
        top = tk.Toplevel(self)
        top.attributes("-fullscreen", True)
        top.attributes("-alpha", 0.3)
        top.configure(bg="black")
        top.attributes("-topmost", True)

        label = tk.Label(top, text="CLICK ANYWHERE TO SET POSITION", font=("Arial", 30), fg="white", bg="black")
        label.pack(expand=True)

        def on_click(event):
            self.config["pos_x"] = top.winfo_pointerx()
            self.config["pos_y"] = top.winfo_pointery()
            self.lbl_pos.configure(text=f"Current: X={self.config['pos_x']}, Y={self.config['pos_y']}")
            self.save_config()
            top.destroy()
            self.refresh_overlay()

        top.bind("<Button-1>", on_click)
        top.focus_force()

    def toggle_listener(self):
        if not self.is_running:
            self.save_config()
            self.is_running = True
            self.btn_start.configure(text="STOP LISTENER", fg_color="red")
            for entry in self.key_entries:
                entry.configure(state="disabled")
            threading.Thread(target=self.listen_for_keys, daemon=True).start()
        else:
            self.is_running = False
            self.btn_start.configure(text="START LISTENER", fg_color="green")
            for entry in self.key_entries:
                entry.configure(state="normal")
            keyboard.unhook_all()
            if self.overlay: self.overlay.set_opacity(1.0)

    def perform_ping(self):
        if self.config["sound_file"] and os.path.exists(self.config["sound_file"]):
            try:
                sound = pygame.mixer.Sound(self.config["sound_file"])
                sound.play()
            except Exception as e:
                print(f"Sound Error: {e}")

        if self.overlay:
            self.overlay.set_opacity(1.0)
        self.ping_timer = None

    def trigger_action(self):
        if self.ping_timer is not None:
            self.after_cancel(self.ping_timer)
        
        if self.overlay:
            self.overlay.set_opacity(0.1) 
        
        self.ping_timer = self.after(1500, self.perform_ping)

    def listen_for_keys(self):
        valid_keys = [k for k in self.config["trigger_keys"] if k.strip()]
        while self.is_running:
            for key in valid_keys:
                if keyboard.is_pressed(key):
                    self.trigger_action()
                    while keyboard.is_pressed(key):
                        time.sleep(0.05)
                    time.sleep(0.1)
                    break
            time.sleep(0.05)

    def on_close(self):
        self.is_running = False
        keyboard.unhook_all()
        self.destroy()
        os._exit(0)