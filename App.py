import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk  # For a modern UI
import keyboard
import pygame
import threading
import json
import os
import time

from Config import CONFIG_FILE, DEFAULT_CONFIG
from FlashOverlay import FlashOverlay


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Ping Overlay Tool")
        self.geometry("400x500")
        self.resizable(False, False)

        self.config = self.load_config()
        self.is_running = False
        self.listener_thread = None

        # --- UI LAYOUT ---
        ctk.CTkLabel(self, text="Ping Tool Settings", font=("Roboto", 20, "bold")).pack(pady=20)

        # 1. Trigger Key
        frame_key = ctk.CTkFrame(self)
        frame_key.pack(pady=10, fill="x", padx=20)
        ctk.CTkLabel(frame_key, text="Trigger Key:").pack(side="left", padx=10)
        self.entry_key = ctk.CTkEntry(frame_key, width=100)
        self.entry_key.insert(0, self.config["trigger_key"])
        self.entry_key.pack(side="right", padx=10)

        # 2. Sound File
        frame_sound = ctk.CTkFrame(self)
        frame_sound.pack(pady=10, fill="x", padx=20)
        self.btn_sound = ctk.CTkButton(frame_sound, text="Select Sound (WAV/MP3)", command=self.select_sound)
        self.btn_sound.pack(fill="x", padx=10, pady=5)
        self.lbl_sound = ctk.CTkLabel(frame_sound,
                                      text=os.path.basename(self.config["sound_file"]) or "No file selected",
                                      text_color="gray")
        self.lbl_sound.pack(pady=5)

        # 3. Graphic File
        frame_img = ctk.CTkFrame(self)
        frame_img.pack(pady=10, fill="x", padx=20)
        self.btn_img = ctk.CTkButton(frame_img, text="Select Graphic (PNG)", command=self.select_image)
        self.btn_img.pack(fill="x", padx=10, pady=5)
        self.lbl_img = ctk.CTkLabel(frame_img, text=os.path.basename(self.config["flash_image"]) or "No file selected",
                                    text_color="gray")
        self.lbl_img.pack(pady=5)

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

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                return json.load(f)
        return DEFAULT_CONFIG

    def save_config(self):
        self.config["trigger_key"] = self.entry_key.get()
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config, f)

    def select_sound(self):
        path = filedialog.askopenfilename(filetypes=[("Audio", "*.wav *.mp3")])
        if path:
            self.config["sound_file"] = path
            self.lbl_sound.configure(text=os.path.basename(path))
            self.save_config()

    def select_image(self):
        path = filedialog.askopenfilename(filetypes=[("Images", "*.png *.jpg")])
        if path:
            self.config["flash_image"] = path
            self.lbl_img.configure(text=os.path.basename(path))
            self.save_config()

    def pick_position(self):
        # Create a transparent full-screen window to capture click
        # We need to capture the virtual screen size for multi-monitors
        # user32 approach ensures we get total size of all monitors combined
        import ctypes
        user32 = ctypes.windll.user32
        screensize = user32.GetSystemMetrics(78), user32.GetSystemMetrics(
            79)  # 78=SM_CXVIRTUALSCREEN, 79=SM_CYVIRTUALSCREEN

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

        top.bind("<Button-1>", on_click)
        top.focus_force()

    def toggle_listener(self):
        if not self.is_running:
            # Start
            self.save_config()
            self.is_running = True
            self.btn_start.configure(text="STOP LISTENER", fg_color="red")
            self.entry_key.configure(state="disabled")

            # Start the keyboard hook in a separate thread
            threading.Thread(target=self.listen_for_keys, daemon=True).start()
        else:
            # Stop
            self.is_running = False
            self.btn_start.configure(text="START LISTENER", fg_color="green")
            self.entry_key.configure(state="normal")
            keyboard.unhook_all()

    def trigger_action(self):
        # 1. Play Sound (Non-blocking)
        if self.config["sound_file"] and os.path.exists(self.config["sound_file"]):
            try:
                sound = pygame.mixer.Sound(self.config["sound_file"])
                sound.play()
            except Exception as e:
                print(f"Sound Error: {e}")

        # 2. Flash Graphic (Must be done on main thread usually, but Tkinter is tricky here.
        # Since we are in a keyboard thread, we must be careful.)
        # The safest way is to schedule it on the main loop, but for a simple overlay,
        # firing a temporary Toplevel usually works okay.
        try:
            FlashOverlay(self.config["pos_x"], self.config["pos_y"], self.config["flash_image"])
        except Exception as e:
            print(f"Graphic Error: {e}")

    def listen_for_keys(self):
        key = self.config["trigger_key"]
        print(f"Listening for {key}...")

        while self.is_running:
            if keyboard.is_pressed(key):
                self.trigger_action()
                # Debounce: Wait for key release + small delay so it doesn't spam
                while keyboard.is_pressed(key):
                    time.sleep(0.05)
                time.sleep(0.1)
            time.sleep(0.05)

    def on_close(self):
        self.is_running = False
        keyboard.unhook_all()
        self.destroy()
        os._exit(0)