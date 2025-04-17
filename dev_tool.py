# This Python program is created for academic purposes only.
# Modification and commercial use are allowed with proper attribution to the author.

# This code is the main entry point for the program's UI, developed based on moderngl window

# Author: [YiHeng FENG]
# Affiliation: [Lab. AAA, School of Architecture, Southeast University, Nanjing]

import logging
import os
import sys

logging.basicConfig(level=logging.INFO,
                    format="%(levelname)-8s %(asctime)-24s %(filename)-24s:%(lineno)-4d | %(message)s")
logging.getLogger("PIL").setLevel(logging.WARNING)  # Disable PIL's DEBUG output
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add dev folder to sys.path
path = os.path.join(os.getcwd(), "dev")
if path not in sys.path:
    sys.path.append(path)

# We use imgui and moderngl_window to render the gui and window, the backend by default is pyglet

# Set DPI scaling, the following two lines can be disabled
import ctypes

ctypes.windll.user32.SetProcessDPIAware()

from dev.window_events import WindowEvents

if __name__ == '__main__':
    WindowEvents.run()
