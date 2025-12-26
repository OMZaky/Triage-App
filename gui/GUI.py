import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import subprocess
import threading
import time
import random
import math
import sys
import os

# =============================================================================
# PHASE 1: THE BACKEND BRIDGE (CONNECTS PYTHON TO C++)
# =============================================================================
class SystemBridge:
    def __init__(self, exe_path):
        self.exe_path = exe_path
        self.process = None
        self.is_running = False

    def start(self):
        """Launches the C++ backend."""
        try:
            # Use appropriate startup info to hide console window on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            self.process = subprocess.Popen(
                [self.exe_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                startupinfo=startupinfo
            )
            self.is_running = True
            return True
        except FileNotFoundError:
            return False

    def send_command(self, cmd):
        """Sends a text command to C++."""
        if not self.is_running: return None
        try:
            self.process.stdin.write(cmd + "\n")
            self.process.stdin.flush()
        except OSError:
            self.is_running = False

    def read_line(self):
        """Reads a single line from C++ output."""
        if not self.is_running: return None
        try:
            return self.process.stdout.readline().strip()
        except OSError:
            return None

    def close(self):
        """Clean shutdown."""
        if self.is_running:
            self.send_command("EXIT")
            self.process.terminate()
            self.is_running = False

# =============================================================================
# PHASE 2 & 3: THE MEDICAL DASHBOARD (VISUALS + LOGIC)
# =============================================================================

# --- THEME CONFIGURATION ---
THEME = {
    "bg_main": "#121212",       # Deep Black
    "bg_sidebar": "#1e1e1e",    # Dark Grey Sidebar
    "card_bg": "#252526",       # Card Background
    "text": "#e0e0e0",          # White Text
    "dim": "#757575",           # Dim Text
    "cyan": "#00e5ff",          # Stable Status
    "red": "#ff1744",           # Critical Status
    "green": "#00e676",         # Success/Vitals
    "orange": "#ff9100",        # Warning
    "grid": "#333333"           # EKG Grid
}

class PatientModel:
    """Stores local state for the GUI simulation"""
    def __init__(self, pid, name, age, prio, condition):
        self.id = pid
        self.name = name
        self.age = age
        self.prio = int(prio)
        self.condition = condition
        
        # Simulation Vitals
        self.hr = random.randint(60, 90) if self.prio > 1 else random.randint(120, 160)
        self.spo2 = random.randint(95, 100) if self.prio > 1 else random.randint(80, 92)
        self.bp_sys = 120
        self.bp_dia = 80
        
        # EKG Data (History of 100 points)
        self.ekg_data = [100] * 100 
        self.tick_phase = 0

    def update_vitals(self):
        """Jitters the numbers to look alive"""
        noise = random.randint(-1, 1)
        self.hr = max(40, min(180, self.hr + noise))
        self.spo2 = max(0, min(100, self.spo2 + (random.choice([-1, 0, 1]) if random.random() > 0.8 else 0)))

class ERDashboard:
    def __init__(self, root, bridge):
        self.root = root
        self.bridge = bridge
        self.patients = [] # List of PatientModel objects
        self.selected_patient = None
        self.running = True

        self.root.title("TriageOS | Critical Care System")
        self.root.geometry("1280x800")
        self.root.configure(bg=THEME["bg_main"])
        
        # Build the Interface
        self.setup_header()
        self.setup_layout()
        self.setup_sidebar()
        self.setup_monitor()
        self.setup_controls()

        # Start the background listener for C++ responses
        self.listen_thread = threading.Thread(target=self.cpp_listener, daemon=True)
        self.listen_thread.start()

        # Start Animation Loop
        self.animate()

    # --- UI SETUP ---
    def setup_header(self):
        header = tk.Frame(self.root, bg=THEME["bg_sidebar"], height=60)
        header.pack(fill="x", side="top")
        
        tk.Label(header, text="TRIAGE O.S.", font=("Eurostile", 20, "bold"), fg=THEME["cyan"], bg=THEME["bg_sidebar"]).pack(side="left", padx=20, pady=10)
        tk.Label(header, text="LIVE CONNECTION: ACTIVE", font=("Segoe UI", 8, "bold"), fg=THEME["green"], bg=THEME["bg_sidebar"]).pack(side="right", padx=20)

    def setup_layout(self):
        # Container for Sidebar + Main
        self.container = tk.Frame(self.root, bg=THEME["bg_main"])
        self.container.pack(fill="both", expand=True)

    def setup_sidebar(self):
        # 1. Sidebar Frame
        self.side_frame = tk.Frame(self.container, bg=THEME["bg_sidebar"], width=320)
        self.side_frame.pack(side="left", fill="y")
        self.side_frame.pack_propagate(False)

        # 2. Header
        tk.Label(self.side_frame, text="ACTIVE BEDS", font=("Segoe UI", 10, "bold"), fg=THEME["dim"], bg=THEME["bg_sidebar"]).pack(anchor="w", padx=15, pady=15)

        # 3. Scrollable Area
        canvas = tk.Canvas(self.side_frame, bg=THEME["bg_sidebar"], highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.side_frame, orient="vertical", command=canvas.yview)
        
        self.bed_list_frame = tk.Frame(canvas, bg=THEME["bg_sidebar"])
        
        self.bed_list_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.bed_list_frame, anchor="nw", width=300)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def setup_monitor(self):
        self.main_view = tk.Frame(self.container, bg=THEME["bg_main"], padx=40, pady=20)
        self.main_view.pack(side="right", fill="both", expand=True)

        # Patient Details Header
        self.lbl_name = tk.Label(self.main_view, text="NO SIGNAL", font=("Eurostile", 40, "bold"), fg=THEME["dim"], bg=THEME["bg_main"], anchor="w")
        self.lbl_name.pack(fill="x")
        
        self.lbl_info = tk.Label(self.main_view, text="Select a bed from the sidebar to initialize monitor.", font=("Consolas", 12), fg=THEME["dim"], bg=THEME["bg_main"], anchor="w")
        self.lbl_info.pack(fill="x", pady=(0, 20))

        # EKG Canvas
        self.monitor_frame = tk.Frame(self.main_view, bg="black", bd=2, relief="sunken")
        self.monitor_frame.pack(fill="x", pady=10)
        
        self.ekg_canvas = tk.Canvas(self.monitor_frame, bg="#050505", height=250, highlightthickness=0)
        self.ekg_canvas.pack(fill="x")
        
        # Grid lines
        for i in range(1, 10):
            self.ekg_canvas.create_line(0, i*25, 1500, i*25, fill="#1a1a1a")
            self.ekg_canvas.create_line(i*50, 0, i*50, 250, fill="#1a1a1a")

        # Vitals Row
        vitals_row = tk.Frame(self.main_view, bg=THEME["bg_main"])
        vitals_row.pack(fill="x", pady=30)

        def make_vital(label, unit, color):
            f = tk.Frame(vitals_row, bg=THEME["bg_main"])
            f.pack(side="left", expand=True)
            tk.Label(f, text=label, font=("Segoe UI", 10), fg=THEME["dim"], bg=THEME["bg_main"]).pack()
            val = tk.Label(f, text="--", font=("Consolas", 48, "bold"), fg=color, bg=THEME["bg_main"])
            val.pack()
            tk.Label(f, text=unit, font=("Segoe UI", 8), fg=THEME["dim"], bg=THEME["bg_main"]).pack()
            return val

        self.val_hr = make_vital("HEART RATE", "BPM", THEME["green"])
        self.val_bp = make_vital("BLOOD PRESSURE", "mmHg", THEME["text"])
        self.val_spo = make_vital("SpO2", "%", THEME["cyan"])

    def setup_controls(self):
        ctrl_frame = tk.Frame(self.main_view, bg=THEME["bg_main"], pady=20)
        ctrl_frame.pack(side="bottom", fill="x")

        # Add Patient Button
        btn_add = tk.Button(ctrl_frame, text="+  ADMIT NEW PATIENT", command=self.popup_add, 
                            bg=THEME["card_bg"], fg="white", font=("Segoe UI", 11, "bold"), relief="flat", padx=20, pady=10)
        btn_add.pack(side="left")

        # Action Buttons
        self.btn_extract = tk.Button(ctrl_frame, text="DISCHARGE / TREAT", command=self.cmd_extract,
                                     bg="#333", fg="white", font=("Segoe UI", 11), relief="flat", padx=20, pady=10, state="disabled")
        self.btn_extract.pack(side="right", padx=10)

        self.btn_update = tk.Button(ctrl_frame, text="!  UPDATE CONDITION", command=self.popup_update,
                                    bg=THEME["bg_main"], fg=THEME["dim"], font=("Segoe UI", 11), relief="flat", padx=20, pady=10, state="disabled")
        self.btn_update.pack(side="right", padx=10)

    # --- LOGIC & COMMUNICATION ---
    def cpp_listener(self):
        """Reads stdin from C++ continuously."""
        while self.running:
            line = self.bridge.read_line()
            if line:
                self.process_cpp_data(line)

    def process_cpp_data(self, line):
        """Parses the raw text from C++."""
        parts = line.split()
        if not parts: return

        cmd = parts[0]
        
        # Format: SUCCESS_ADD Name ID:1
        if cmd == "SUCCESS_ADD":
            # Just a confirmation, visual update happens via local list
            pass
            
        # Format: DATA [ID] [PRIO] [AGE] [NAME] [DESC]
        elif cmd == "DATA":
            pid = int(parts[1])
            prio = int(parts[2])
            age = int(parts[3])
            name = parts[4]
            desc = " ".join(parts[5:]) # Join remaining words
            
            # This is called when we EXTRACT or PEEK. 
            # If extracting, we remove from local list.
            # (Logic handled in command functions mostly)
            pass

    def refresh_sidebar(self):
        """Redraws the sidebar list from local data."""
        # Clear
        for w in self.bed_list_frame.winfo_children(): w.destroy()

        # Sort: Prio 1 first, then ID
        self.patients.sort(key=lambda x: (x.prio, x.id))

        for p in self.patients:
            # Card Style
            color = THEME["red"] if p.prio == 1 else THEME["cyan"]
            bg = "#333" if self.selected_patient == p else THEME["card_bg"]
            
            card = tk.Frame(self.bed_list_frame, bg=bg, pady=10, padx=10)
            card.pack(fill="x", pady=1)

            # Left Color Strip
            tk.Frame(card, bg=color, width=4, height=35).pack(side="left", padx=(0, 10))

            # Info
            info = tk.Frame(card, bg=bg)
            info.pack(side="left", fill="both")
            tk.Label(info, text=p.name, font=("Segoe UI", 11, "bold"), fg=THEME["text"], bg=bg, anchor="w").pack(fill="x")
            tk.Label(info, text=f"ID: {p.id} | AGE: {p.age} | P: {p.prio}", font=("Segoe UI", 8), fg=THEME["dim"], bg=bg, anchor="w").pack(fill="x")
            
            # Click Event
            bind_click(card, p, self.select_patient)
            bind_click(info, p, self.select_patient)

    def select_patient(self, p):
        self.selected_patient = p
        self.refresh_sidebar() # Update selection highlight
        
        # Update UI
        color = THEME["red"] if p.prio == 1 else THEME["cyan"]
        self.lbl_name.config(text=p.name.upper(), fg=color)
        self.lbl_info.config(text=f"ID: {p.id}  |  AGE: {p.age}  |  CONDITION: {p.condition.upper()}")
        
        self.btn_extract.config(state="normal", bg=THEME["green"], text="DISCHARGE / TREAT")
        self.btn_update.config(state="normal", bg="#333", fg="white")

    # --- COMMANDS ---
    def popup_add(self):
        # In a real app, this would be a nice modal. Using simpledialog for brevity.
        name = simpledialog.askstring("Admit", "Patient Name:")
        if not name: return
        age = simpledialog.askinteger("Admit", "Age:")
        if not age: return
        prio = simpledialog.askinteger("Admit", "Priority (1-10):", minvalue=1, maxvalue=10)
        if not prio: return
        desc = simpledialog.askstring("Admit", "Condition/Description:")
        if not desc: desc = "Unknown"

        # 1. Send to C++
        # CMD: ADD [PRIO] [AGE] [NAME] [DESC]
        # (Assuming Name has no spaces for simplicity, or replace space with _)
        safe_name = name.replace(" ", "_")
        safe_desc = desc.replace(" ", "_")
        self.bridge.send_command(f"ADD {prio} {age} {safe_name} {safe_desc}")
        
        # 2. Update Local State (We simulate the ID since C++ auto-increments but doesn't return ID instantly in sync)
        # For the demo, we assume ID increments.
        next_id = 1 if not self.patients else max(p.id for p in self.patients) + 1
        new_p = PatientModel(next_id, name, age, prio, desc)
        self.patients.append(new_p)
        self.refresh_sidebar()

    def cmd_extract(self):
        # 1. Send to C++
        self.bridge.send_command("EXTRACT")
        
        # 2. Logic: C++ extracts the Min (highest priority). 
        # We need to find who that is locally to remove them.
        if not self.patients: return
        
        # Find the one with highest priority (lowest number)
        target = min(self.patients, key=lambda x: (x.prio, x.id))
        
        # Update GUI to show "Discharged"
        self.lbl_name.config(text=f"TREATING {target.name.upper()}...", fg=THEME["green"])
        self.root.update()
        time.sleep(0.5) # Fake processing delay
        
        self.patients.remove(target)
        self.selected_patient = None
        
        # Reset View
        self.lbl_name.config(text="NO SIGNAL", fg=THEME["dim"])
        self.val_hr.config(text="--")
        self.val_bp.config(text="--")
        self.val_spo.config(text="--")
        self.btn_extract.config(state="disabled")
        self.refresh_sidebar()

    def popup_update(self):
        if not self.selected_patient: return
        new_prio = simpledialog.askinteger("Update", "New Priority (1=Critical):", minvalue=1, maxvalue=10)
        if not new_prio: return
        
        # 1. Send to C++
        self.bridge.send_command(f"UPDATE {self.selected_patient.id} {new_prio}")
        
        # 2. Local Update
        self.selected_patient.prio = new_prio
        if new_prio == 1: self.selected_patient.condition = "CRITICAL DETERIORATION"
        self.refresh_sidebar()
        self.select_patient(self.selected_patient) # Refresh view

    # --- ANIMATION LOOP ---
    def animate(self):
        if self.selected_patient:
            p = self.selected_patient
            p.update_vitals()
            
            # Update Text
            color = THEME["red"] if p.prio == 1 else THEME["cyan"]
            self.val_hr.config(text=str(p.hr), fg=color)
            self.val_bp.config(text=f"{p.bp_sys}/{p.bp_dia}", fg=color)
            self.val_spo.config(text=f"{p.spo2}", fg=color)

            # EKG Logic
            p.ekg_data.pop(0)
            
            # Create Heartbeat Wave
            val = 200 # Baseline
            interval = 4 if p.prio == 1 else 10 # Faster if critical
            p.tick_phase += 1
            
            mod = p.tick_phase % interval
            if mod == 0: val = 180   # Small up
            elif mod == 1: val = 220 # Dip
            elif mod == 2: val = 50  # SPIKE
            elif mod == 3: val = 230 # Dip
            else: val = 200 + random.randint(-2, 2)
            
            p.ekg_data.append(val)
            
            # Draw
            self.ekg_canvas.delete("line")
            w = self.ekg_canvas.winfo_width()
            points = []
            step = w / len(p.ekg_data)
            for i, y in enumerate(p.ekg_data):
                points.append(i * step)
                points.append(y)
            
            self.ekg_canvas.create_line(points, fill=color, width=2, smooth=True, tags="line")

        self.root.after(50, self.animate)

def bind_click(widget, p, func):
    widget.bind("<Button-1>", lambda e: func(p))
    for child in widget.winfo_children():
        bind_click(child, p, func)

# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    # 1. SETUP BRIDGE
    exe_name = "triage.exe" if os.name == 'nt' else "./triage"
    bridge = SystemBridge(exe_name)
    
    if not bridge.start():
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Error", f"Could not find '{exe_name}'.\nPlease compile the C++ backend first.")
        sys.exit()

    # 2. RUN APP
    root = tk.Tk()
    app = ERDashboard(root, bridge)
    
    # 3. CLEANUP ON CLOSE
    def on_close():
        bridge.close()
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", on_close)
    
    root.mainloop()