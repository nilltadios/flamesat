import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import time
import threading
import queue 

# --- CONFIGURATION ---
THEME = {
    "bg": "#050505",       # Deep Black
    "fg": "#ff3333",       # CRT Red
    "panel": "#111111",    # Dark Grey
    "btn_bg": "#220000",   # Blood Red
    "btn_fg": "#ff9999",   # Pale Red
    # "DejaVu Sans Mono" is the standard crisp terminal font on Fedora
    "font_main": ("DejaVu Sans Mono", 11, "bold"),
    "font_console": ("DejaVu Sans Mono", 9),
    "font_header": ("DejaVu Sans Mono", 18, "bold")
}

# Paths (Relative to where this script lives)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "../logo.png")
START_SCRIPT = os.path.join(BASE_DIR, "start_mission.sh")
STOP_SCRIPT = os.path.join(BASE_DIR, "stop_mission.sh")
PID_FILE = os.path.join(BASE_DIR, "logs/mission.pids")

class MissionControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FLAMESAT COMMAND LINK")
        # Increased height slightly to accommodate vertical stacking
        self.root.geometry("700x600") 
        self.root.configure(bg=THEME["bg"])
        
        # Thread-Safe Queue for logs
        self.log_queue = queue.Queue()
        
        # --- UI LAYOUT ---
        
        # 1. Header & Logo (Centered Stack)
        self.header_frame = tk.Frame(root, bg=THEME["bg"], pady=15)
        self.header_frame.pack(fill="x")
        
        try:
            # Resize logic: 2 means 1/2 size. Adjust if your logo is too big/small.
            self.logo_img = tk.PhotoImage(file=LOGO_PATH).subsample(2, 2)
            self.logo_lbl = tk.Label(self.header_frame, image=self.logo_img, bg=THEME["bg"])
            self.logo_lbl.pack(side="top", anchor="center", pady=(0, 10))
        except Exception:
            self.logo_lbl = tk.Label(self.header_frame, text="[NO IMAGE]", bg=THEME["bg"], fg=THEME["fg"])
            self.logo_lbl.pack(side="top", anchor="center", pady=(0, 10))

        self.title_lbl = tk.Label(self.header_frame, text="FLAMESAT // COMMAND", font=THEME["font_header"], bg=THEME["bg"], fg=THEME["fg"])
        self.title_lbl.pack(side="top", anchor="center")

        # 2. Status Indicator
        self.status_lbl = tk.Label(root, text="SYSTEM OFFLINE", font=THEME["font_main"], bg=THEME["bg"], fg="#666")
        self.status_lbl.pack(pady=(5, 20))

        # 3. Control Buttons
        self.btn_frame = tk.Frame(root, bg=THEME["bg"])
        self.btn_frame.pack(pady=10)

        self.btn_start = tk.Button(self.btn_frame, text="INITIATE UPLINK", command=self.start_mission, 
                                   bg=THEME["btn_bg"], fg=THEME["btn_fg"], font=THEME["font_main"], 
                                   width=20, height=2, activebackground="#ff0000", borderwidth=1, relief="flat")
        self.btn_start.pack(side="left", padx=20)

        self.btn_stop = tk.Button(self.btn_frame, text="TERMINATE LINK", command=self.stop_mission, 
                                  bg="#222", fg="#888", font=THEME["font_main"], 
                                  width=20, height=2, activebackground="#555", borderwidth=1, relief="flat")
        self.btn_stop.pack(side="left", padx=20)

        # 4. Log Console
        self.console_frame = tk.Frame(root, bg=THEME["panel"], padx=2, pady=2)
        self.console_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        self.console = tk.Text(self.console_frame, bg="black", fg="#0f0", 
                               font=THEME["font_console"], height=10, state="disabled", 
                               borderwidth=0, highlightthickness=0)
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        # 5. Start Polling Loops
        self.update_status()
        self.process_log_queue()

    def log(self, message):
        """Thread-safe logging: Put message in queue, don't touch GUI"""
        self.log_queue.put(message)

    def process_log_queue(self):
        """Check queue and update GUI on the main thread"""
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.console.config(state="normal")
                self.console.insert("end", msg + "\n")
                self.console.see("end")
                self.console.config(state="disabled")
            except queue.Empty:
                pass
        
        # Run this function again in 100ms
        self.root.after(100, self.process_log_queue)

    def update_status(self):
        """Check PID file to see if mission is running"""
        if os.path.exists(PID_FILE):
            self.status_lbl.config(text="● UPLINK ACTIVE", fg=THEME["fg"])
            self.btn_start.config(state="disabled", bg="#220000", fg="#550000")
            self.btn_stop.config(state="normal", bg="#333", fg="white")
        else:
            self.status_lbl.config(text="○ SYSTEM STANDBY", fg="#666")
            self.btn_start.config(state="normal", bg=THEME["btn_bg"], fg=THEME["btn_fg"])
            self.btn_stop.config(state="disabled", bg="#111", fg="#444")
        
        self.root.after(2000, self.update_status)

    def start_mission(self):
        self.log(">>> INITIALIZING SEQUENCE...")
        self.btn_start.config(state="disabled")
        
        def run():
            try:
                # Capture output safely
                process = subprocess.Popen([START_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                
                # Read line by line
                for line in iter(process.stdout.readline, ''):
                    self.log(line.strip())
                
                process.stdout.close()
                process.wait()
                
                self.log(">>> SEQUENCE COMPLETE.")
            except Exception as e:
                self.log(f"!!! CRITICAL ERROR: {e}")

        threading.Thread(target=run, daemon=True).start()

    def stop_mission(self):
        self.log(">>> TERMINATING SIGNAL...")
        
        def run():
            try:
                process = subprocess.Popen([STOP_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()
                if stdout: self.log(stdout.strip())
                if stderr: self.log(stderr.strip())
            except Exception as e:
                self.log(f"!!! ERROR: {e}")

        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MissionControlApp(root)
    root.mainloop()