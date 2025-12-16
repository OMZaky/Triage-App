import tkinter as tk
from tkinter import messagebox, font
import subprocess
import os
import sys
import time

# ==========================================
# 1. CONFIGURATION & STYLES
# ==========================================
COLORS = {
    "bg": "#f0f2f5",          # Light Gray Background
    "card": "#ffffff",        # White Container
    "primary": "#0078d4",     # Medical Blue
    "danger": "#d93025",      # Emergency Red
    "success": "#188038",     # Success Green
    "text": "#202124",        # Dark Gray Text
    "subtext": "#5f6368",     # Light Gray Text
    "border": "#dadce0"       # Subtle Border
}

# ==========================================
# 2. BACKEND CONNECTION
# ==========================================
print("--- STARTING VITALSORT UI ---")

script_dir = os.path.dirname(os.path.abspath(__file__))
# Look for app.exe in the parent folder
exe_path = os.path.abspath(os.path.join(script_dir, "..", "app.exe"))

if not os.path.exists(exe_path):
    exe_path = os.path.abspath(os.path.join(script_dir, "..", "app")) # Fallback

if not os.path.exists(exe_path):
    print(f"[ERROR] Backend not found at: {exe_path}")
    sys.exit(1)

try:
    proc = subprocess.Popen(
        [exe_path], 
        stdin=subprocess.PIPE, 
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True, 
        bufsize=1
    )
    print("[INFO] Backend Connected.")
except Exception as e:
    print(f"[CRASH] Backend failed: {e}")
    sys.exit(1)

# ==========================================
# 3. LOGIC FUNCTIONS
# ==========================================

def send_cmd(command):
    if proc.poll() is not None: return "ERROR: Backend Dead"
    try:
        proc.stdin.write(command + "\n")
        proc.stdin.flush()
        return proc.stdout.readline().strip()
    except: return "ERROR: IO Fail"

def safe_exit():
    try:
        send_cmd("EXIT")
        time.sleep(0.2)
        if proc.poll() is None: proc.terminate()
    except: pass
    root.destroy()
    sys.exit(0)

# --- NEW: STATS UPDATE FUNCTION ---
def update_stats():
    """Silently asks C++ for current queue size and wait time."""
    resp = send_cmd("STATS")
    if "STATS" in resp:
        # Expected format: STATS COUNT:5 WAIT:75
        try:
            parts = resp.split()
            count_part = parts[1].split(":")[1]
            wait_part = parts[2].split(":")[1]
            
            # These labels are created in Section 4 (Layout)
            lbl_wait_time.config(text=f"{wait_part} min")
            lbl_queue_count.config(text=f"{count_part} Patients")
        except:
            pass # Ignore parsing errors during startup

def perform_login():
    pwd = entry_pass.get()
    resp = send_cmd(f"LOGIN {pwd}")
    if "SUCCESS" in resp:
        login_frame.pack_forget()
        main_layout.pack(fill="both", expand=True)
        # Trigger the first stats update
        update_stats()
    else:
        lbl_login_err.config(text="Access Denied: Incorrect Password", fg=COLORS["danger"])

def add_patient():
    p_name = entry_name.get()
    p_age = entry_age.get()
    p_prio = entry_prio.get()
    p_desc = entry_desc.get()
    
    # Validation
    if not p_name or not p_age or not p_prio or not p_desc:
        lbl_status.config(text="⚠ All fields required", fg=COLORS["danger"])
        return

    if not p_age.isdigit():
        lbl_status.config(text="⚠ Age must be a number", fg=COLORS["danger"])
        return
        
    if not p_prio.isdigit() or int(p_prio) < 1 or int(p_prio) > 10:
        lbl_status.config(text="⚠ Priority must be 1-10", fg=COLORS["danger"])
        return

    # Underscore Protocol
    safe_name = p_name.replace(" ", "_")
    safe_desc = p_desc.replace(" ", "_")

    resp = send_cmd(f"ADD {p_prio} {p_age} {safe_name} {safe_desc}")
    
    if "SUCCESS" in resp:
        parts = resp.split(":")
        new_id = parts[1] if len(parts) > 1 else "?"
        lbl_status.config(text=f"✔ Registered ID {new_id}", fg=COLORS["success"])
        
        # Clear fields
        entry_name.delete(0, tk.END)
        entry_age.delete(0, tk.END)
        entry_prio.delete(0, tk.END)
        entry_desc.delete(0, tk.END)
        
        # Refresh Dashboard Stats
        update_stats()
    else:
        lbl_status.config(text=f"Error: {resp}", fg=COLORS["danger"])

def extract_patient():
    resp = send_cmd("EXTRACT")
    if "EMPTY" in resp:
        lbl_big_status.config(text="No Critical Patients", fg=COLORS["subtext"])
        lbl_patient_detail.config(text="Queue is empty")
    elif "DATA" in resp:
        # Parse: DATA [ID] [PRIO] [AGE] [NAME] [DESC]
        parts = resp.split() 
        if len(parts) >= 6:
            p_id = parts[1]
            p_prio = parts[2]
            p_age = parts[3]
            p_name = parts[4].replace("_", " ")
            p_desc = parts[5].replace("_", " ")
            
            lbl_big_status.config(text=f"Treating: {p_name}", fg=COLORS["primary"])
            lbl_patient_detail.config(text=f"ID: {p_id} | Age: {p_age} | Priority: {p_prio}\n\nCondition: {p_desc}")
    
    # Refresh Dashboard Stats
    update_stats()

# ==========================================
# 4. GUI COMPONENTS (LAYOUT)
# ==========================================
root = tk.Tk()
root.title("VitalSort Triage System")
root.geometry("1000x650")
root.configure(bg=COLORS["bg"])
root.protocol("WM_DELETE_WINDOW", safe_exit)

# Custom Fonts
f_header = ("Segoe UI", 24, "bold")
f_sub = ("Segoe UI", 12)
f_norm = ("Segoe UI", 10)
f_bold = ("Segoe UI", 10, "bold")

# --- LOGIN SCREEN ---
login_frame = tk.Frame(root, bg=COLORS["bg"])
login_card = tk.Frame(login_frame, bg=COLORS["card"], padx=40, pady=40, relief="flat")
login_card.place(relx=0.5, rely=0.5, anchor="center")

tk.Label(login_card, text="VitalSort", font=f_header, bg=COLORS["card"], fg=COLORS["primary"]).pack(pady=(0, 5))
tk.Label(login_card, text="Hospital Triage Administration", font=f_sub, bg=COLORS["card"], fg=COLORS["subtext"]).pack(pady=(0, 20))

tk.Label(login_card, text="Admin Password", font=f_bold, bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w")
entry_pass = tk.Entry(login_card, show="•", font=f_sub, width=25, relief="solid", bd=1)
entry_pass.pack(pady=5, ipady=5)
entry_pass.bind('<Return>', lambda e: perform_login())

btn_login = tk.Button(login_card, text="Sign In", command=perform_login, bg=COLORS["primary"], fg="white", 
                      font=f_bold, relief="flat", cursor="hand2", padx=20, pady=8)
btn_login.pack(pady=20, fill="x")
lbl_login_err = tk.Label(login_card, text="", font=f_norm, bg=COLORS["card"], fg=COLORS["danger"])
lbl_login_err.pack()

login_frame.pack(fill="both", expand=True)

# --- MAIN DASHBOARD ---
main_layout = tk.Frame(root, bg=COLORS["bg"])

# HEADER
header = tk.Frame(main_layout, bg="white", height=60, padx=20)
header.pack(fill="x", side="top")
tk.Label(header, text="VitalSort", font=("Segoe UI", 18, "bold"), fg=COLORS["primary"], bg="white").pack(side="left", pady=15)
tk.Label(header, text="Dr. Admin", font=f_norm, fg=COLORS["text"], bg="white").pack(side="right", pady=15)

# CONTENT CONTAINER
content = tk.Frame(main_layout, bg=COLORS["bg"], padx=20, pady=20)
content.pack(fill="both", expand=True)

# LEFT COLUMN: INPUT FORM
left_col = tk.Frame(content, bg=COLORS["card"], width=320, padx=20, pady=20)
left_col.pack(side="left", fill="y", padx=(0, 20))
left_col.pack_propagate(False)

tk.Label(left_col, text="Register Patient", font=("Segoe UI", 14, "bold"), bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", pady=(0, 20))

def create_input(label, entry_var):
    tk.Label(left_col, text=label, font=f_bold, bg=COLORS["card"], fg=COLORS["subtext"]).pack(anchor="w")
    e = tk.Entry(left_col, textvariable=entry_var, font=f_norm, relief="solid", bd=1)
    e.pack(fill="x", pady=(5, 15), ipady=5)
    return e

entry_name = create_input("Full Name", None)
entry_age = create_input("Age", None)
entry_prio = create_input("Triage Score (1-10)", None)
entry_desc = create_input("Condition Description", None)

btn_add = tk.Button(left_col, text="+ Register Patient", command=add_patient, bg=COLORS["success"], fg="white", 
                    font=f_bold, relief="flat", cursor="hand2", pady=10)
btn_add.pack(fill="x", pady=10)
lbl_status = tk.Label(left_col, text="System Ready", font=f_norm, bg=COLORS["card"], fg=COLORS["subtext"])
lbl_status.pack(pady=10)

# RIGHT COLUMN: ACTION CENTER & STATS
right_col = tk.Frame(content, bg=COLORS["bg"])
right_col.pack(side="left", fill="both", expand=True)

# 1. NEW: Stats Row (Wait Time & Count)
stats_frame = tk.Frame(right_col, bg=COLORS["bg"])
stats_frame.pack(fill="x", pady=(0, 20))

def create_stat_card(parent, title, color):
    card = tk.Frame(parent, bg=COLORS["card"], padx=20, pady=15)
    card.pack(side="left", fill="x", expand=True, padx=5)
    tk.Label(card, text=title, font=("Segoe UI", 10, "bold"), bg=COLORS["card"], fg=COLORS["subtext"]).pack(anchor="w")
    lbl = tk.Label(card, text="0", font=("Segoe UI", 20, "bold"), bg=COLORS["card"], fg=color)
    lbl.pack(anchor="w")
    return lbl

# THESE ARE THE VARIABLES THAT WERE "UNDEFINED" BEFORE
lbl_wait_time = create_stat_card(stats_frame, "Est. Wait Time", COLORS["danger"])
lbl_queue_count = create_stat_card(stats_frame, "Patients in Queue", COLORS["primary"])

# 2. Existing Status Card
status_card = tk.Frame(right_col, bg=COLORS["card"], padx=30, pady=30)
status_card.pack(fill="x", pady=(0, 20))

tk.Label(status_card, text="Current Triage Action", font=("Segoe UI", 10, "bold"), bg=COLORS["card"], fg=COLORS["subtext"]).pack(anchor="w")
lbl_big_status = tk.Label(status_card, text="Waiting for Input...", font=("Segoe UI", 18, "bold"), bg=COLORS["card"], fg=COLORS["text"])
lbl_big_status.pack(pady=10, anchor="w")
lbl_patient_detail = tk.Label(status_card, text="-", font=("Segoe UI", 11), bg=COLORS["card"], fg=COLORS["primary"], justify="left")
lbl_patient_detail.pack(anchor="w")

# 3. Existing Extract Button
btn_extract = tk.Button(right_col, text="CALL NEXT PATIENT", command=extract_patient, bg=COLORS["danger"], fg="white", 
                        font=("Segoe UI", 12, "bold"), relief="flat", cursor="hand2", pady=15)
btn_extract.pack(fill="x")

# --- INITIALIZATION ---
root.lift()
root.mainloop()