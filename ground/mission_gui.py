import tkinter as tk
from tkinter import messagebox
import subprocess
import os
import time
import threading
import queue 
import socket
import json

# --- CONFIGURATION ---
THEME = {
    "bg": "#050505",
    "fg": "#ff3333",
    "panel": "#111111",
    "btn_bg": "#220000",
    "btn_fg": "#ff9999",
    "btn_cmd": "#333333",
    "input_bg": "#0a0a0a",
    "input_fg": "#00ff00",
    "font_main": ("DejaVu Sans Mono", 11, "bold"),
    "font_console": ("DejaVu Sans Mono", 9),
    "font_header": ("DejaVu Sans Mono", 18, "bold")
}

SAT_HOST = "flamesat.local"
CMD_PORT = 5001
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGO_PATH = os.path.join(BASE_DIR, "../logo.png")
START_SCRIPT = os.path.join(BASE_DIR, "start_mission.sh")
STOP_SCRIPT = os.path.join(BASE_DIR, "stop_mission.sh")
PID_FILE = os.path.join(BASE_DIR, "logs/mission.pids")
SECRETS_FILE = os.path.join(BASE_DIR, "secrets.json")

class MissionControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FLAMESAT COMMAND LINK")
        self.root.geometry("700x800") 
        self.root.configure(bg=THEME["bg"])
        self.log_queue = queue.Queue()

        # Load Password
        self.auth_token = None
        try:
            with open(SECRETS_FILE) as f:
                secrets = json.load(f)
                self.auth_token = secrets.get("command_password")
        except: pass

        if not self.auth_token:
            messagebox.showwarning("SECURITY ALERT", "No 'command_password' found in secrets.json.\nUplink will be rejected by Satellite.")
        
        # --- UI LAYOUT ---
        self.header_frame = tk.Frame(root, bg=THEME["bg"], pady=15)
        self.header_frame.pack(fill="x")
        try:
            self.logo_img = tk.PhotoImage(file=LOGO_PATH).subsample(2, 2)
            self.logo_lbl = tk.Label(self.header_frame, image=self.logo_img, bg=THEME["bg"])
            self.logo_lbl.pack(side="top", anchor="center", pady=(0, 10))
        except: pass
        tk.Label(self.header_frame, text="FLAMESAT // COMMAND", font=THEME["font_header"], bg=THEME["bg"], fg=THEME["fg"]).pack(side="top")

        self.status_lbl = tk.Label(root, text="SYSTEM OFFLINE", font=THEME["font_main"], bg=THEME["bg"], fg="#666")
        self.status_lbl.pack(pady=(5, 10))

        self.btn_frame = tk.Frame(root, bg=THEME["bg"])
        self.btn_frame.pack(pady=10)
        self.btn_start = self.create_btn(self.btn_frame, "INITIATE UPLINK", self.start_mission, THEME["btn_bg"], THEME["btn_fg"])
        self.btn_start.pack(side="left", padx=10)
        self.btn_stop = self.create_btn(self.btn_frame, "TERMINATE LINK", self.stop_mission, "#222", "#888")
        self.btn_stop.pack(side="left", padx=10)

        # Command Section
        self.shell_frame = tk.LabelFrame(root, text=" SECURE COMMAND UPLINK ", font=THEME["font_console"], 
                                         bg=THEME["bg"], fg="#666", bd=1, relief="solid")
        self.shell_frame.pack(pady=10, padx=20, fill="x")

        self.cmd_entry = tk.Entry(self.shell_frame, bg=THEME["input_bg"], fg=THEME["input_fg"], 
                                  insertbackground="white", font=THEME["font_console"], relief="flat")
        self.cmd_entry.pack(side="left", fill="x", expand=True, padx=10, pady=10)
        self.cmd_entry.bind('<Return>', lambda event: self.send_manual_command())

        self.btn_send = tk.Button(self.shell_frame, text="SEND >", command=self.send_manual_command, 
                                  bg="#333", fg="white", font=THEME["font_console"], relief="flat")
        self.btn_send.pack(side="right", padx=10, pady=10)

        self.quick_frame = tk.Frame(root, bg=THEME["bg"])
        self.quick_frame.pack(pady=10)
        tk.Button(self.quick_frame, text="SHUTDOWN SAT", command=lambda: self.send_command("sudo shutdown now"), 
                  bg="#550000", fg="white", font=("DejaVu Sans Mono", 9), relief="flat").pack(side="left", padx=5)
        tk.Button(self.quick_frame, text="REBOOT SAT", command=lambda: self.send_command("sudo reboot"), 
                  bg="#444", fg="white", font=("DejaVu Sans Mono", 9), relief="flat").pack(side="left", padx=5)

        self.console_frame = tk.Frame(root, bg=THEME["panel"], padx=2, pady=2)
        self.console_frame.pack(fill="both", expand=True, padx=20, pady=20)
        self.console = tk.Text(self.console_frame, bg="black", fg="#0f0", font=THEME["font_console"], height=10, state="disabled", bd=0)
        self.console.pack(fill="both", expand=True, padx=5, pady=5)

        self.update_status()
        self.process_log_queue()

    def create_btn(self, parent, text, cmd, bg, fg):
        return tk.Button(parent, text=text, command=cmd, bg=bg, fg=fg, font=THEME["font_main"], 
                         width=20, height=2, activebackground="#fff", borderwidth=1, relief="flat")

    def log(self, message):
        self.log_queue.put(message)

    def process_log_queue(self):
        while not self.log_queue.empty():
            try:
                msg = self.log_queue.get_nowait()
                self.console.config(state="normal")
                self.console.insert("end", msg + "\n")
                self.console.see("end")
                self.console.config(state="disabled")
            except queue.Empty: pass
        self.root.after(100, self.process_log_queue)

    def send_manual_command(self):
        cmd = self.cmd_entry.get()
        if cmd.strip():
            self.send_command(cmd)
            self.cmd_entry.delete(0, 'end')

    def send_command(self, cmd_code):
        if not self.auth_token:
            self.log("!!! ERROR: No Auth Token configured.")
            return

        self.log(f"root@ground:~# {cmd_code}")
        
        def run():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(10)
                s.connect((SAT_HOST, CMD_PORT))
                
                # AUTHENTICATION: Prepend the password
                secure_payload = f"{self.auth_token}|{cmd_code}"
                s.sendall(secure_payload.encode())
                
                response = s.recv(4096).decode().strip()
                if response: self.log(response)
                else: self.log("[No Output]")
                s.close()
            except Exception as e:
                self.log(f"!!! UPLINK FAILED: {e}")
        threading.Thread(target=run, daemon=True).start()

    def update_status(self):
        if os.path.exists(PID_FILE):
            self.status_lbl.config(text="● UPLINK ACTIVE", fg=THEME["fg"])
            self.btn_start.config(state="disabled", bg="#220000")
            self.btn_stop.config(state="normal", bg="#333")
        else:
            self.status_lbl.config(text="○ SYSTEM STANDBY", fg="#666")
            self.btn_start.config(state="normal", bg=THEME["btn_bg"])
            self.btn_stop.config(state="disabled", bg="#111")
        self.root.after(2000, self.update_status)

    def start_mission(self):
        self.log(">>> INITIALIZING SEQUENCE...")
        self.btn_start.config(state="disabled")
        def run():
            try:
                process = subprocess.Popen([START_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                for line in iter(process.stdout.readline, ''): self.log(line.strip())
                process.stdout.close()
                process.wait()
                self.log(">>> SEQUENCE COMPLETE.")
            except Exception as e: self.log(f"!!! CRITICAL ERROR: {e}")
        threading.Thread(target=run, daemon=True).start()

    def stop_mission(self):
        self.log(">>> TERMINATING SIGNAL...")
        def run():
            try:
                process = subprocess.Popen([STOP_SCRIPT], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                out, err = process.communicate()
                if out: self.log(out.strip())
                if err: self.log(err.strip())
            except Exception as e: self.log(f"!!! ERROR: {e}")
        threading.Thread(target=run, daemon=True).start()

if __name__ == "__main__":
    root = tk.Tk()
    app = MissionControlApp(root)
    root.mainloop()