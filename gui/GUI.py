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
# 2. BACKEND CONNECTION (Robust)
# ==========================================
print("--- STARTING VITALSORT UI ---")

script_dir = os.path.dirname(os.path.abspath(__file__))
exe_path = os.path.abspath(os.path.join(script_dir, "..", "app.exe"))

if not os.path.exists(exe_path):
    exe_path = os.path.abspath(os.path.join(script_dir, "..", "app")) # Linux/Mac fallback

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

def perform_login():
    pwd = entry_pass.get()
    resp = send_cmd(f"LOGIN {pwd}")
    if "SUCCESS" in resp:
        login_frame.pack_forget()
        main_layout.pack(fill="both", expand=True)
    else:
        lbl_login_err.config(text="Access Denied: Incorrect Password", fg=COLORS["danger"])

def add_patient():
    p_id, p_prio, p_name = entry_id.get(), entry_prio.get(), entry_name.get()
    if not p_id or not p_prio or not p_name:
        lbl_status.config(text="⚠ Missing Fields", fg=COLORS["danger"])
        return
    
    clean_name = p_name.replace(" ", "_")
    resp = send_cmd(f"ADD {p_id} {p_prio} {clean_name}")
    
    if "SUCCESS" in resp:
        lbl_status.config(text=f"✔ Registered: {p_name}", fg=COLORS["success"])
        entry_id.delete(0, tk.END)
        entry_prio.delete(0, tk.END)
        entry_name.delete(0, tk.END)
    else:
        lbl_status.config(text=f"Error: {resp}", fg=COLORS["danger"])

def extract_patient():
    resp = send_cmd("EXTRACT")
    if "EMPTY" in resp:
        lbl_big_status.config(text="No Critical Patients", fg=COLORS["subtext"])
        lbl_patient_detail.config(text="Queue is empty")
    elif "DATA" in resp:
        parts = resp.split() # DATA ID PRIO NAME
        if len(parts) >= 4:
            p_name = parts[3].replace("_", " ")
            lbl_big_status.config(text=f"Treating: {p_name}", fg=COLORS["primary"])
            lbl_patient_detail.config(text=f"ID: {parts[1]}  |  Priority Score: {parts[2]}")

# ==========================================
# 4. GUI COMPONENTS (MODERN STYLING)
# ==========================================
root = tk.Tk()
root.title("VitalSort Triage System")
root.geometry("900x600")
root.configure(bg=COLORS["bg"])
root.protocol("WM_DELETE_WINDOW", safe_exit)

# Custom Fonts
f_header = ("Segoe UI", 24, "bold")
f_sub = ("Segoe UI", 12)
f_norm = ("Segoe UI", 10)
f_bold = ("Segoe UI", 10, "bold")

# --- LOGIN SCREEN (Centered Card) ---
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

# --- MAIN DASHBOARD (Split Layout) ---
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
left_col = tk.Frame(content, bg=COLORS["card"], width=300, padx=20, pady=20)
left_col.pack(side="left", fill="y", padx=(0, 20))
left_col.pack_propagate(False) # Force width

tk.Label(left_col, text="Register Patient", font=("Segoe UI", 14, "bold"), bg=COLORS["card"], fg=COLORS["text"]).pack(anchor="w", pady=(0, 20))

def create_input(label, entry_var):
    tk.Label(left_col, text=label, font=f_bold, bg=COLORS["card"], fg=COLORS["subtext"]).pack(anchor="w")
    e = tk.Entry(left_col, textvariable=entry_var, font=f_norm, relief="solid", bd=1)
    e.pack(fill="x", pady=(5, 15), ipady=5)
    return e

entry_name = tk.Entry(left_col) # Dummy init
entry_name = create_input("Full Name", None)
entry_id = create_input("Patient ID", None)
entry_prio = create_input("Triage Score (1=Critical)", None)

btn_add = tk.Button(left_col, text="+ Register Patient", command=add_patient, bg=COLORS["success"], fg="white", 
                    font=f_bold, relief="flat", cursor="hand2", pady=10)
btn_add.pack(fill="x", pady=10)
lbl_status = tk.Label(left_col, text="System Ready", font=f_norm, bg=COLORS["card"], fg=COLORS["subtext"])
lbl_status.pack(pady=10)

# RIGHT COLUMN: ACTION CENTER
right_col = tk.Frame(content, bg=COLORS["bg"])
right_col.pack(side="left", fill="both", expand=True)

# Status Card
status_card = tk.Frame(right_col, bg=COLORS["card"], padx=30, pady=40)
status_card.pack(fill="x", pady=(0, 20))

tk.Label(status_card, text="Current Action Required", font=f_bold, bg=COLORS["card"], fg=COLORS["subtext"]).pack()
lbl_big_status = tk.Label(status_card, text="Waiting for Input...", font=("Segoe UI", 24, "bold"), bg=COLORS["card"], fg=COLORS["text"])
lbl_big_status.pack(pady=10)
lbl_patient_detail = tk.Label(status_card, text="-", font=("Segoe UI", 12), bg=COLORS["card"], fg=COLORS["primary"])
lbl_patient_detail.pack()

# Big Action Button
btn_extract = tk.Button(right_col, text="CALL NEXT PATIENT", command=extract_patient, bg=COLORS["danger"], fg="white", 
                        font=("Segoe UI", 14, "bold"), relief="flat", cursor="hand2", pady=20)
btn_extract.pack(fill="x")

# --- INITIALIZATION ---
root.lift()
root.mainloop()