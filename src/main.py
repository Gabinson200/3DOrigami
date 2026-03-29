# src/main.py
import sys
import os

# Ensure the src directory is accessible for absolute imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.ui.app_window import OrigamiThickenerUI

def main():
    app = OrigamiThickenerUI()
    app.mainloop()

if __name__ == "__main__":
    main()
