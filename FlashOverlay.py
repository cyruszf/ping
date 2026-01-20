import tkinter as tk
from PIL import Image, ImageTk, ImageDraw, ImageOps
import ctypes
import time
import os
import threading

class FlashOverlay:
    def __init__(self, image_path, scale=1.0): 
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 1.0)
        
        # Transparent Window Setup
        self.transparent_key = "#000001"
        self.root.wm_attributes("-transparentcolor", self.transparent_key)
        self.root.configure(bg=self.transparent_key)

        self.canvas = tk.Canvas(self.root, bg=self.transparent_key, highlightthickness=0, bd=0)
        self.canvas.pack()
        self.image_item = None
        
        # --- LOAD ASSETS ---
        self.icon_pil = None
        self.frame_pil = None
        
        try:
            self.icon_pil = Image.open(image_path).convert("RGBA")
            print(f"[OK] Icon loaded.")
        except Exception as e:
            print(f"[ERROR] Icon failed: {e}")

        if os.path.exists("frame.png"):
            try:
                self.frame_pil = Image.open("frame.png").convert("RGBA")
                print("[OK] frame.png loaded.")
            except:
                pass
        
        # Animation Cache
        self.tk_frames = []         # Final Images ready for screen
        self.pil_frames = []        # Raw data from thread
        self.anim_job = None
        self.is_ready = False
        
        # Initial Draw
        if self.icon_pil:
            self.resize_graphic(scale)

        self.make_click_through()

    def resize_graphic(self, scale):
        if not self.icon_pil: return
        
        # 1. Dimensions
        w = int(self.icon_pil.width * scale)
        h = int(self.icon_pil.height * scale)
        if w < 1: w = 1
        if h < 1: h = 1
        self.width, self.height = w, h
        self.canvas.config(width=w, height=h)
        
        # 2. Prepare Layers
        # Layer A: Bright Color (Foreground)
        self.base_color = self.icon_pil.resize((w, h), Image.Resampling.LANCZOS)
        
        # Layer B: Black & White (Background)
        gray_temp = ImageOps.grayscale(self.base_color).convert("RGBA")
        gray_temp.putalpha(self.base_color.getchannel("A"))
        self.base_bw = gray_temp
        
        # Layer C: Frame (Top)
        self.base_frame = None
        if self.frame_pil:
            self.base_frame = self.frame_pil.resize((w, h), Image.Resampling.LANCZOS)

        # 3. Show Static "Ready" Image Immediately
        ready_comp = self.base_color.copy()
        if self.base_frame:
            ready_comp = Image.alpha_composite(ready_comp, self.base_frame)
            
        self.img_ready = self.convert_to_tk(ready_comp)
        
        if self.image_item:
            self.canvas.itemconfig(self.image_item, image=self.img_ready)
        else:
            self.image_item = self.canvas.create_image(0, 0, image=self.img_ready, anchor="nw")
        
        self.root.update()

        # 4. Start Heavy Processing in Thread
        self.is_ready = False
        self.pil_frames = [] # Clear old cache
        threading.Thread(target=self.generate_raw_frames, daemon=True).start()
        
        # 5. Start Polling for results
        self.check_thread_completion()

    def generate_raw_frames(self):
        """ THREAD: Generates pure PIL images (Heavy Math) """
        print("Thread: Generating 60 frames...")
        frames = []
        total_frames = 60

        for i in range(total_frames):
            pct = i / (total_frames - 1)
            
            # Start with Black & White
            frame = self.base_bw.copy()
            
            # Create Wipe Mask
            mask = Image.new("L", (self.width, self.height), 0)
            draw = ImageDraw.Draw(mask)
            end_angle = -90 + (360 * pct)
            bbox = [-10, -10, self.width+10, self.height+10]
            draw.pieslice(bbox, start=-90, end=end_angle, fill=255)
            
            # Paste Color
            frame.paste(self.base_color, (0, 0), mask=mask)
            
            # Paste Frame
            if self.base_frame:
                frame = Image.alpha_composite(frame, self.base_frame)
            
            # Store raw image
            frames.append(frame)

        # Send to main thread
        self.pil_frames = frames

    def check_thread_completion(self):
        """ MAIN THREAD: Checks if raw frames are ready and converts them """
        if self.pil_frames:
            # Thread finished! Convert to Tkinter images now.
            # This is fast, but must happen on Main Thread.
            print("Main: Converting frames to graphics...")
            self.tk_frames = [self.convert_to_tk(img) for img in self.pil_frames]
            self.is_ready = True
            print("Main: Animation Ready.")
        else:
            # Check again in 100ms
            self.root.after(100, self.check_thread_completion)

    def convert_to_tk(self, pil_img):
        """ Helper to convert PIL -> PhotoImage safely """
        bg_img = Image.new("RGBA", pil_img.size, self.transparent_key + "FF") 
        bg_img.paste(pil_img, (0, 0), mask=pil_img)
        return ImageTk.PhotoImage(bg_img.convert("RGB"))

    def start_cooldown_animation(self, duration_ms):
        # Fallback if animation not ready
        if not self.is_ready or not self.tk_frames:
            self.set_opacity(0.7)
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