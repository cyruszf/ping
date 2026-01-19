import pygame
from App import App

# --- AUDIO ENGINE ---
pygame.mixer.init()

if __name__ == "__main__":
    app = App()
    app.mainloop()