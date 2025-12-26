"""
TriageOS - Main Entry Point (Robust Architecture)
The application root window that manages view switching (Login <-> Dashboard).

ARCHITECTURE:
    TriageApp (CTk) - The one and only window
        ├── LoginFrame (CTkFrame) - Swapped in for login
        └── DashboardFrame (CTkFrame) - Swapped in after login
"""

import customtkinter as ctk
from tkinter import messagebox
import sys
import os

# Configure CustomTkinter before importing other modules
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

# Import our modules
# NOTE: Ensure login_window.py has 'class LoginFrame(ctk.CTkFrame)'
# NOTE: Ensure dashboard.py has 'class DashboardFrame(ctk.CTkFrame)'
from bridge import SystemBridge
from login_window import LoginFrame
from dashboard import DashboardFrame


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


class TriageApp(ctk.CTk):
    """
    The single root window for TriageOS.
    Manages switching between Login and Dashboard frames.
    """
    
    def __init__(self, bridge: SystemBridge):
        super().__init__()
        
        self.bridge = bridge
        self.current_frame = None
        
        # Window configuration
        self.title("TRIAGE O.S. - Emergency Room Management")
        self.geometry("1400x850")
        self.minsize(1000, 700)
        self.configure(fg_color="#1a1a2e") # Dark Navy Background
        
        # Center window on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 700
        y = (self.winfo_screenheight() // 2) - 425
        self.geometry(f"+{x}+{y}")
        
        # Handle window close (X button)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start with login screen
        self.show_login()
    
    def _clear_current_frame(self) -> None:
        """
        Remove the current frame from the window.
        CRITICAL: Calls cleanup() if the frame has it to stop threads/sounds.
        """
        if self.current_frame is not None:
            # Call cleanup if available (DashboardFrame has it)
            if hasattr(self.current_frame, 'cleanup'):
                try:
                    self.current_frame.cleanup()
                except Exception:
                    pass
            
            # Destroy the frame
            try:
                self.current_frame.destroy()
            except Exception:
                pass
            
            self.current_frame = None
    
    def show_login(self) -> None:
        """Show the login frame."""
        self._clear_current_frame()
        
        # Instantiate LoginFrame (Pass 'self' as master)
        self.current_frame = LoginFrame(
            master=self,
            bridge=self.bridge,
            on_success_callback=self.show_dashboard
        )
        self.current_frame.pack(fill="both", expand=True)
    
    def show_dashboard(self) -> None:
        """Show the dashboard frame."""
        self._clear_current_frame()
        
        # Instantiate DashboardFrame (Pass 'self' as master)
        self.current_frame = DashboardFrame(
            master=self,
            bridge=self.bridge,
            on_logout_callback=self.logout_handler
        )
        self.current_frame.pack(fill="both", expand=True)
    
    def logout_handler(self) -> None:
        """Handle logout - cleanup dashboard and show login."""
        # Mark as logging out so bridge stays open
        if hasattr(self.current_frame, 'is_logging_out'):
            self.current_frame.is_logging_out = True
        
        self.show_login()
    
    def _on_close(self) -> None:
        """
        Handle window close (X button).
        CRITICAL: Must cleanup current frame before destroying window.
        """
        # Cleanup current frame (stops threads, alarm, etc.)
        self._clear_current_frame()
        
        # Close the bridge
        try:
            if self.bridge:
                self.bridge.close()
        except Exception:
            pass
        
        # Destroy the window and exit
        self.destroy()
        sys.exit(0)


def main():
    """Main entry point."""
    print("=" * 50)
    print("  TRIAGE O.S. - Emergency Room Management")
    print("=" * 50)
    
    # Step 1: Find the backend executable
    exe_path = find_backend_executable()
    
    if exe_path is None:
        root = ctk.CTk()
        root.withdraw()
        messagebox.showerror(
            "Backend Not Found",
            "Could not find 'triage.exe'.\n\nPlease compile the C++ backend first."
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
            "Failed to start the C++ backend.\nCheck the console for error details."
        )
        root.destroy()
        sys.exit(1)
    
    print("[Main] C++ backend started successfully")
    
    # Step 3: Run the application
    app = TriageApp(bridge)
    app.mainloop()
    
    print("[Main] Application closed")


if __name__ == "__main__":
    main()