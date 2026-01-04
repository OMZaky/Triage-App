"""
TriageOS - Main Entry Point (Robust Architecture)
The application root window that manages view switching (Login <-> Dashboard).

ARCHITECTURE:
    TriageApp (CTk) - The one and only window
        ├── LoginFrame (CTkFrame) - Swapped in for login
        └── DashboardFrame (CTkFrame) - Swapped in after login
"""

# =============================================================================
# WINDOWS DPI FIX - Must be FIRST before any GUI imports
# Fixes blurry/mangled text on high-DPI displays
# =============================================================================
try:
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)  # 1 = System DPI aware
except Exception:
    pass  # Non-Windows or older Windows - ignore

import customtkinter as ctk
from tkinter import messagebox, font as tkfont
import sys
import os

# =============================================================================
# CUSTOMTKINTER SCALING - Prevent auto-scaling glitches
# =============================================================================
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")
ctk.set_widget_scaling(1.0)   # 1.0 = no scaling, 1.25 = 25% larger
ctk.set_window_scaling(1.0)


def get_system_font() -> str:
    """
    Get the best available system font with cross-platform fallback.
    Returns: Font family name that exists on this system.
    """
    preferred_fonts = ["Segoe UI", "Helvetica Neue", "Helvetica", "Arial", "sans-serif"]
    
    try:
        # Get list of available fonts on this system
        available = tkfont.families()
        for font_name in preferred_fonts:
            if font_name in available:
                return font_name
    except Exception:
        pass
    
    # Ultimate fallback
    return "TkDefaultFont"


# Store the system font for use throughout the app
SYSTEM_FONT = get_system_font()

# Import our modules
# NOTE: Ensure login_window.py has 'class LoginFrame(ctk.CTkFrame)'
# NOTE: Ensure dashboard.py has 'class DashboardFrame(ctk.CTkFrame)'
from bridge import SystemBridge
from login_window import LoginFrame
from dashboard import DashboardFrame
from theme import COLORS


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
    
    FRAME SWAP ARCHITECTURE:
    - Starts with LoginFrame
    - On successful login, swaps to DashboardFrame
    - On logout, swaps back to LoginFrame
    """
    
    def __init__(self, bridge: SystemBridge):
        super().__init__()
        
        self.bridge = bridge
        self.current_frame = None
        
        # Window configuration
        self.title("TRIAGE O.S. - Emergency Room Management")
        self.minsize(1000, 700)
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Responsive Sizing: Adapt to screen size
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        # Store dimensions for deterministic centering
        self.app_width = min(1400, int(screen_w * 0.90))
        self.app_height = min(850, int(screen_h * 0.85))
        
        # Center immediately using stored dimensions
        self.center_on_screen()
        
        # Handle window close (X button)
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Start with login screen
        self.show_login()
    
    def center_on_screen(self) -> None:
        """Centers the main window using deterministic dimensions."""
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        
        # Calculate Position using stored dimensions (NOT winfo_width)
        x = (screen_w - self.app_width) // 2
        y = (screen_h - self.app_height) // 2 - 40  # Shift up for taskbar
        
        # Safety checks
        x = max(0, x)
        y = max(0, y)
        
        # Apply Size AND Position in one atomic command
        self.geometry(f"{self.app_width}x{self.app_height}+{x}+{y}")
        
        # Force focus to front
        self.deiconify()
        self.lift()
    
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
        
        # Use the LoginFrame from login_window.py
        self.current_frame = LoginFrame(
            master=self,
            bridge=self.bridge,
            on_success_callback=self.show_dashboard
        )
        # LoginFrame packs itself in __init__, but just in case:
        if not self.current_frame.winfo_ismapped():
            self.current_frame.pack(fill="both", expand=True)
    
    def show_dashboard(self) -> None:
        """Show the dashboard frame."""
        self._clear_current_frame()
        
        # Create DashboardFrame
        self.current_frame = DashboardFrame(
            master=self,
            bridge=self.bridge,
            on_logout_callback=self.logout_handler
        )
        self.current_frame.pack(fill="both", expand=True)
        
        # Activate dashboard by fetching initial data
        self.after(100, self._activate_dashboard)
    
    def _activate_dashboard(self) -> None:
        """Send initial commands to populate dashboard after login."""
        if self.current_frame and hasattr(self.current_frame, '_enqueue_command'):
            self.current_frame._enqueue_command("STATS")
            self.current_frame._enqueue_command("LIST")
            print("[Main] Dashboard activated - Loading patient data")
    
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