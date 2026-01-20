import tkinter as tk


class FlashOverlay:
    def __init__(self, image_path):  # We only need the path once
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.attributes("-alpha", 1.0)
        self.root.wm_attributes("-transparentcolor", "white")

        # Load image once
        try:
            self.img = tk.PhotoImage(file=image_path)
            self.width = self.img.width()
            self.height = self.img.height()
        except:
            self.img = None
            self.width = 100
            self.height = 100

        if self.img:
            lbl = tk.Label(self.root, image=self.img, bg='white')
            lbl.pack()
        else:
            lbl = tk.Label(self.root, text="PING", bg='red', fg='white', font=("Arial", 20))
            lbl.pack()

        # Hide immediately after creation
        self.root.withdraw()

    def flash(self, x, y):
        # 1. Move to new position
        new_x = int(x - self.width / 2)
        new_y = int(y - self.height / 2)
        self.root.geometry(f"{self.width}x{self.height}+{new_x}+{new_y}")

        # 2. Show
        self.root.deiconify()

        # 3. Schedule Hide (not destroy)
        self.root.after(500, self.root.withdraw)