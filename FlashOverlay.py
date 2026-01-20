import tkinter as tk
from PIL import Image, ImageTk 
import ctypes

class FlashOverlay:
    def __init__(self, image_path, scale=1.0): 
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 1.0)
        
        self.transparent_key = "#000001"
        self.root.wm_attributes("-transparentcolor", self.transparent_key)
        self.root.configure(bg=self.transparent_key)

        try:
            self.original_pil = Image.open(image_path).convert("RGBA")
        except Exception as e:
            print(f"Load Error: {e}")
            self.original_pil = None

        self.lbl = tk.Label(self.root, bg=self.transparent_key, bd=0, highlightthickness=0)
        self.lbl.pack()

        # Initial Draw
        if self.original_pil:
            self.resize_graphic(scale)
        else:
            self.lbl.configure(text="READY", bg='green', fg='white', font=("Arial", 20))

        self.root.update()
        self.make_click_through()

    def resize_graphic(self, scale):
        if not self.original_pil: return

        try:
            # Renders exactly the size requested (Logic is handled in App.py)
            w = int(self.original_pil.width * scale)
            h = int(self.original_pil.height * scale)
            
            if w < 1: w = 1
            if h < 1: h = 1
            
            pil_img = self.original_pil.resize((w, h), Image.Resampling.BILINEAR)
            
            # Clean Edges (Anti-Scuff)
            bg_img = Image.new("RGBA", pil_img.size, self.transparent_key + "FF") 
            r, g, b, a = pil_img.split()
            mask = a.point(lambda p: 255 if p > 64 else 0)
            bg_img.paste(pil_img, (0, 0), mask=mask)
            final_img = bg_img.convert("RGB")
            
            self.img = ImageTk.PhotoImage(final_img)
            self.width = w
            self.height = h
            
            self.lbl.configure(image=self.img)
            
        except Exception as e:
            print(f"Resize Error: {e}")

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