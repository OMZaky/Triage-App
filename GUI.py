import tkinter as tk
from tkinter import messagebox
import subprocess

# ASSIGNED TO: MEMBER 5

# --- CONNECT TO C++ ---
# Ensure you compile with: g++ main.cpp System.cpp FibHeap.cpp Node.cpp Auth.cpp -o app
proc = subprocess.Popen(
    ['./app'], # Use 'app.exe' on Windows
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)

def send_cmd(cmd):
    proc.stdin.write(cmd + "\n")
    proc.stdin.flush()
    return proc.stdout.readline().strip()

# --- GUI LOGIC ---
def login():
    pwd = entry_pass.get()
    resp = send_cmd(f"LOGIN {pwd}")
    if "SUCCESS" in resp:
        login_frame.pack_forget()
        app_frame.pack()
    else:
        messagebox.showerror("Error", "Invalid Password")

def add_patient():
    id_val = entry_id.get()
    prio = entry_prio.get()
    name = entry_name.get()
    # Send: ADD [ID] [PRIO] [NAME]
    resp = send_cmd(f"ADD {id_val} {prio} {name}")
    lbl_status.config(text=resp)

def next_patient():
    resp = send_cmd("EXTRACT")
    if "EMPTY" in resp:
        messagebox.showinfo("Info", "No patients waiting.")
    else:
        # Parse "DATA 101 5 John"
        parts = resp.split()
        lbl_current.config(text=f"Treating: {parts[3]} (Priority: {parts[2]})")


def on_closing():
    if messagebox.askokcancel("Quit", "Do you want to save and quit?"):
        # Tell C++ to save
        send_cmd("EXIT") 
        root.destroy() # Close the window

# --- LAYOUT ---
root = tk.Tk()
root.title("VitalSort - Hospital Triage")
root.geometry("400x300")

# FRAME 1: LOGIN
login_frame = tk.Frame(root)
tk.Label(login_frame, text="Admin Password").pack(pady=5)
entry_pass = tk.Entry(login_frame, show="*")
entry_pass.pack(pady=5)
tk.Button(login_frame, text="Login", command=login).pack(pady=10)
login_frame.pack(fill="both", expand=True)

# FRAME 2: APP (Hidden)
app_frame = tk.Frame(root)
tk.Label(app_frame, text="New Patient Name:").pack()
entry_name = tk.Entry(app_frame)
entry_name.pack()

tk.Label(app_frame, text="Priority (1-10):").pack()
entry_prio = tk.Entry(app_frame)
entry_prio.pack()

tk.Label(app_frame, text="ID:").pack()
entry_id = tk.Entry(app_frame)
entry_id.pack()

tk.Button(app_frame, text="Add Patient", command=add_patient).pack(pady=5)
tk.Button(app_frame, text="Treat Next Critical", command=next_patient, bg="red", fg="white").pack(pady=10)

lbl_current = tk.Label(app_frame, text="Waiting...", font=("Arial", 12))
lbl_current.pack()

lbl_status = tk.Label(app_frame, text="System Ready", fg="gray")
lbl_status.pack(side="bottom")

root.protocol("WM_DELETE_WINDOW", on_closing)

root.mainloop()