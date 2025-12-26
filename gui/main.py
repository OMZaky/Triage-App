"""
TriageOS - Main Entry Point (CustomTkinter)
Launches the Emergency Room Triage Management System.
Supports Login -> Dashboard -> Logout -> Login cycle.
"""

import customtkinter as ctk
from tkinter import messagebox
import sys
import os

# Configure CustomTkinter before importing other modules
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Import our modules
from bridge import SystemBridge
from login_window import LoginWindow
from dashboard import ERDashboard


def find_backend_executable() -> str | None:
    """
    Locate the C++ backend executable.
    Searches common locations relative to the script.
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    
    possible_paths = [
        os.path.join(project_root, "triage.exe"),
        os.path.join(project_root, "triage"),
        os.path.join(project_root, "build", "triage.exe"),
        os.path.join(project_root, "build", "triage"),
        os.path.join(script_dir, "..", "triage.exe"),
        os.path.join(script_dir, "triage.exe"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return os.path.abspath(path)
    
    return None


def main():
    """
    Main entry point for the TriageOS application.
    
    Flow (with logout support):
    1. Find and start the C++ backend
    2. LOOP:
       a. Show LoginWindow
       b. If login fails/closes -> break loop, exit
       c. If login succeeds -> launch Dashboard
       d. If logout clicked -> continue loop (back to login)
       e. If dashboard closed normally -> break loop, exit
    3. Cleanup and exit
    """
    print("=" * 50)
    print("  TRIAGE O.S. - Emergency Room Management")
    print("  CustomTkinter Modern UI Edition")
    print("=" * 50)
    
    # Step 1: Find the backend executable
    exe_path = find_backend_executable()
    
    if exe_path is None:
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror(
            "Backend Not Found",
            "Could not find 'triage.exe'.\n\n"
            "Please compile the C++ backend first:\n"
            "g++ src/*.cpp -o triage.exe"
        )
        root.destroy()
        sys.exit(1)
    
    print(f"[Main] Found backend at: {exe_path}")
    
    # Step 2: Create and start the bridge
    bridge = SystemBridge(exe_path)
    
    if not bridge.start():
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror(
            "Startup Error",
            "Failed to start the C++ backend.\n"
            "Check the console for error details."
        )
        root.destroy()
        sys.exit(1)
    
    print("[Main] C++ backend started successfully")
    
    # Step 3: Main application loop (Login -> Dashboard -> Logout -> Login)
    while True:
        # Track login and logout state
        login_successful = False
        user_logged_out = False
        
        def on_login_success():
            """Called when login succeeds."""
            nonlocal login_successful
            login_successful = True
        
        # Show login window
        print("[Main] Showing login window...")
        login = LoginWindow(bridge, on_login_success)
        login.mainloop()
        
        # Check if login was successful
        if not login_successful:
            print("[Main] Login cancelled or failed, exiting...")
            break
        
        # Define logout callback
        def on_logout():
            """Called when user clicks Logout in dashboard."""
            nonlocal user_logged_out
            user_logged_out = True
            print("[Main] User logged out")
        
        # Launch dashboard
        print("[Main] Launching dashboard...")
        dashboard = ERDashboard(bridge, on_logout_callback=on_logout)
        dashboard.mainloop()
        
        # Check if user logged out (continue loop) or closed normally (exit)
        if user_logged_out:
            print("[Main] Returning to login screen...")
            continue
        else:
            print("[Main] Dashboard closed, exiting...")
            break
    
    # Step 4: Cleanup
    bridge.close()
    print("[Main] Application closed")


if __name__ == "__main__":
    main()
