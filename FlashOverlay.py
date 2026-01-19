import tkinter as tk

class FlashOverlay:
    def __init__(self, x, y, image_path):
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)  # Remove borders
        self.root.attributes("-topmost", True)  # Stay on top
        self.root.attributes("-alpha", 1.0)  # Opacity

        # Keep it from stealing focus from the game
        self.root.wm_attributes("-transparentcolor", "white")

        try:
            # Load and resize image to be visible but not huge
            self.img = tk.PhotoImage(file=image_path)
            # You might want to resize if the image is huge,
            # but Tkinter PhotoImage scaling is tricky.
            # Best to provide a 200x200 png.
        except:
            # Fallback red square if no image found
            self.img = None

        if self.img:
            lbl = tk.Label(self.root, image=self.img, bg='white')
            lbl.pack()
            # Center the window on the coordinate
            w = self.img.width()
            h = self.img.height()
            self.root.geometry(f"{w}x{h}+{int(x - w / 2)}+{int(y - h / 2)}")
        else:
            lbl = tk.Label(self.root, text="PING", bg='red', fg='white', font=("Arial", 20))
            lbl.pack()
            self.root.geometry(f"100x100+{int(x - 50)}+{int(y - 50)}")

        # Auto destroy after 500ms
        self.root.after(500, self.root.destroy)
        # Ensure it draws immediately
        self.root.update()
