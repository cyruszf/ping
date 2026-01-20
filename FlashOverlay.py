import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageOps, ImageEnhance
import ctypes
import time
import os
import threading
import sys

# --- FIX FOR SINGLE FILE EXE ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class FlashOverlay:
    def __init__(self, image_path, scale=1.0): 
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        # FORCE 100% OPACITY ALWAYS
        self.root.attributes("-alpha", 1.0) 
        
        self.transparent_key = "#000001"
        self.root.wm_attributes("-transparentcolor", self.transparent_key)
        self.root.configure(bg=self.transparent_key)

        self.canvas = tk.Canvas(self.root, bg=self.transparent_key, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.image_item = None
        
        self.icon_pil = None
        self.frame_pil = None
        
        try:
            self.icon_pil = Image.open(resource_path(image_path)).convert("RGBA")
        except Exception as e:
            print(f"Error loading icon: {e}")

        if os.path.exists(resource_path("frame.png")):
            try:
                self.frame_pil = Image.open(resource_path("frame.png")).convert("RGBA")
            except:
                pass
        
        self.tk_frames = []        
        self.pil_frames = []       
        self.anim_job = None
        self.is_ready = False
        
        if self.icon_pil:
            self.resize_graphic(scale)

        self.make_click_through()

    def resize_graphic(self, scale):
        if not self.icon_pil: return
        w = int(self.icon_pil.width * scale)
        h = int(self.icon_pil.height * scale)
        if w < 1: w = 1
        if h < 1: h = 1
        self.width, self.height = w, h
        self.canvas.config(width=w, height=h)
        
        self.base_color = self.icon_pil.resize((w, h), Image.Resampling.LANCZOS)
        
        # --- MAKE THE COOLDOWN BRIGHTER ---
        # Instead of dark gray, we make it a bright gray so it feels solid
        gray_temp = ImageOps.grayscale(self.base_color).convert("RGBA")
        enhancer = ImageEnhance.Brightness(gray_temp)
        gray_temp = enhancer.enhance(1.5) # 50% Brighter
        gray_temp.putalpha(self.base_color.getchannel("A"))
        self.base_bw = gray_temp
        # ----------------------------------
        
        self.base_frame = None
        if self.frame_pil:
            self.base_frame = self.frame_pil.resize((w, h), Image.Resampling.LANCZOS)

        ready_comp = self.base_color.copy()
        if self.base_frame:
            ready_comp = Image.alpha_composite(ready_comp, self.base_frame)
            
        self.img_ready = self.convert_to_tk(ready_comp)
        
        if self.image_item:
            self.canvas.itemconfig(self.image_item, image=self.img_ready)
        else:
            self.image_item = self.canvas.create_image(0, 0, image=self.img_ready, anchor="nw")
        
        self.root.update()

        self.is_ready = False
        self.pil_frames = []
        threading.Thread(target=self.generate_raw_frames, daemon=True).start()
        self.check_thread_completion()

    def generate_raw_frames(self):
        frames = []
        total_frames = 60
        for i in range(total_frames):
            pct = i / (total_frames - 1)
            frame = self.base_bw.copy()
            
            mask = Image.new("L", (self.width, self.height), 0)
            draw = ImageDraw.Draw(mask)
            end_angle = -90 + (360 * pct)
            bbox = [-10, -10, self.width+10, self.height+10]
            draw.pieslice(bbox, start=-90, end=end_angle, fill=255)
            
            frame.paste(self.base_color, (0, 0), mask=mask)
            
            if self.base_frame:
                frame = Image.alpha_composite(frame, self.base_frame)
            
            frames.append(frame)
        self.pil_frames = frames

    def check_thread_completion(self):
        if self.pil_frames:
            self.tk_frames = [self.convert_to_tk(img) for img in self.pil_frames]
            self.is_ready = True
        else:
            self.root.after(100, self.check_thread_completion)

    def convert_to_tk(self, pil_img):
        bg_img = Image.new("RGBA", pil_img.size, self.transparent_key + "FF") 
        bg_img.paste(pil_img, (0, 0), mask=pil_img)
        return ImageTk.PhotoImage(bg_img.convert("RGB"))

    def start_cooldown_animation(self, duration_ms):
        # --- HERE IS THE FIX ---
        # Even if animation is loading, STAY 100% SOLID
        if not self.is_ready or not self.tk_frames:
            self.set_opacity(1.0)  # Forced Solid
            self.root.after(duration_ms, lambda: self.set_opacity(1.0))
            return

        if self.anim_job:
            self.root.after_cancel(self.anim_job)

        start_time = time.time()
        total_frames = len(self.tk_frames)

        def play_frame():
            now = time.time()
            elapsed = (now - start_time) * 1000 
            progress = elapsed / duration_ms
            
            if progress >= 1.0:
                self.canvas.itemconfig(self.image_item, image=self.img_ready)
                return

            idx = int(progress * total_frames)
            if idx >= total_frames: idx = total_frames - 1
            
            self.canvas.itemconfig(self.image_item, image=self.tk_frames[idx])
            self.anim_job = self.root.after(16, play_frame)

        play_frame()

    def make_click_through(self):
        try:
            WS_EX_TRANSPARENT = 0x00000020
            WS_EX_LAYERED = 0x00080000
            GWL_EXSTYLE = -20
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if hwnd == 0: hwnd = self.root.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = style | WS_EX_TRANSPARENT | WS_EX_LAYERED
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        except:
            pass

    def set_opacity(self, alpha):
        self.root.attributes("-alpha", alpha)

    def move_to(self, x, y):
        if hasattr(self, 'width'):
            new_x = int(x - self.width / 2)
            new_y = int(y - self.height / 2)
            self.root.geometry(f"{self.width}x{self.height}+{new_x}+{new_y}")