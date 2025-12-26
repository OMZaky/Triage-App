"""
TriageOS - Login Window Module (CustomTkinter)
Modern authentication GUI for the medical triage system.
Uses CustomTkinter for a professional dark-mode appearance.
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
from typing import Callable, Optional

# Import the bridge for backend communication
from bridge import SystemBridge

# Configure CustomTkinter appearance
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


class LoginWindow(ctk.CTk):
    """
    Modern authentication window for TriageOS using CustomTkinter.
    
    Features:
    - Sleek dark-mode design
    - Placeholder text in entry fields
    - Smooth button hover effects
    - Background thread for C++ response handling
    
    Usage:
        def on_success():
            print("Logged in!")
        
        app = LoginWindow(bridge, on_success)
        app.mainloop()
    """
    
    # Color scheme
    COLORS = {
        "bg_dark": "#1a1a2e",
        "bg_card": "#16213e",
        "accent": "#00d4ff",
        "accent_hover": "#00a8cc",
        "text": "#ffffff",
        "text_muted": "#a0a0a0",
        "error": "#ff4757",
        "success": "#2ed573",
    }
    
    def __init__(self, bridge: SystemBridge, on_success_callback: Callable[[], None]):
        """
        Initialize the login window.
        
        Args:
            bridge: SystemBridge instance for C++ communication
            on_success_callback: Function to call upon successful login
        """
        super().__init__()
        
        self.bridge = bridge
        self.on_success_callback = on_success_callback
        self.is_logged_in = False
        
        # Window configuration
        self.title("TRIAGE O.S. - Login")
        self.geometry("400x500")
        self.resizable(False, False)
        self.configure(fg_color=self.COLORS["bg_dark"])
        
        # Center window on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - 200
        y = (self.winfo_screenheight() // 2) - 250
        self.geometry(f"+{x}+{y}")
        
        # Build the UI
        self._create_widgets()
        
        # Start listening for C++ responses
        self._start_listener()
        
        # Focus the username entry
        self.user_entry.focus()
    
    def _create_widgets(self) -> None:
        """Create the modern login form."""
        
        # Main container with padding
        container = ctk.CTkFrame(self, fg_color=self.COLORS["bg_card"], corner_radius=20)
        container.pack(expand=True, fill="both", padx=30, pady=30)
        
        # === Logo/Title Section ===
        logo_label = ctk.CTkLabel(
            container,
            text="🏥",
            font=ctk.CTkFont(size=60)
        )
        logo_label.pack(pady=(30, 10))
        
        title_label = ctk.CTkLabel(
            container,
            text="TRIAGE O.S.",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=self.COLORS["accent"]
        )
        title_label.pack(pady=(0, 5))
        
        subtitle_label = ctk.CTkLabel(
            container,
            text="Emergency Room Management System",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["text_muted"]
        )
        subtitle_label.pack(pady=(0, 30))
        
        # === Login Form ===
        form_frame = ctk.CTkFrame(container, fg_color="transparent")
        form_frame.pack(fill="x", padx=40)
        
        # Username Entry
        self.user_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Username",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            border_width=2,
            border_color=self.COLORS["accent"]
        )
        self.user_entry.pack(fill="x", pady=(0, 15))
        
        # Password Entry
        self.pass_entry = ctk.CTkEntry(
            form_frame,
            placeholder_text="Password",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            border_width=2,
            border_color=self.COLORS["accent"],
            show="•"
        )
        self.pass_entry.pack(fill="x", pady=(0, 20))
        
        # Error Label (hidden initially)
        self.error_label = ctk.CTkLabel(
            form_frame,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["error"]
        )
        self.error_label.pack(pady=(0, 10))
        
        # Login Button
        self.login_btn = ctk.CTkButton(
            form_frame,
            text="Login",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
            command=self._attempt_login
        )
        self.login_btn.pack(fill="x", pady=(10, 0))
        
        # === Footer ===
        footer_label = ctk.CTkLabel(
            container,
            text="Secure Medical Triage Platform",
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS["text_muted"]
        )
        footer_label.pack(side="bottom", pady=20)
        
        # Bind Enter key to login
        self.bind("<Return>", lambda e: self._attempt_login())
    
    def _attempt_login(self) -> None:
        """Attempt to login with the entered credentials."""
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()
        
        # Validate input
        if not username:
            self._show_error("Please enter a username")
            self.user_entry.focus()
            return
        
        if not password:
            self._show_error("Please enter a password")
            self.pass_entry.focus()
            return
        
        # Disable button during login attempt
        self.login_btn.configure(state="disabled", text="Authenticating...")
        self._clear_error()
        
        # Send login command to C++ backend
        if not self.bridge.send_command(f"LOGIN {username} {password}"):
            self._show_error("Failed to connect to backend")
            self.login_btn.configure(state="normal", text="Login")
    
    def _start_listener(self) -> None:
        """Start a background thread to listen for C++ responses."""
        
        def listen():
            while not self.is_logged_in:
                try:
                    # Check if window still exists
                    if not self.winfo_exists():
                        break
                except Exception:
                    break
                
                try:
                    line = self.bridge.read_line()
                    
                    if line is None:
                        continue
                    
                    if line == "SUCCESS_LOGIN":
                        self.is_logged_in = True
                        try:
                            self.after(0, self._on_login_success)
                        except Exception:
                            pass
                        break
                        
                    elif line == "ERROR_LOGIN":
                        try:
                            if self.winfo_exists():
                                self.after(0, self._on_login_failed)
                        except Exception:
                            pass
                except Exception:
                    break
        
        thread = threading.Thread(target=listen, daemon=True)
        thread.start()
    
    def _on_login_success(self) -> None:
        """Handle successful login - transition to dashboard."""
        print("[Login] Authentication successful")
        
        # Destroy the login window
        self.destroy()
        
        # Call the success callback to launch dashboard
        self.on_success_callback()
    
    def _on_login_failed(self) -> None:
        """Handle failed login attempt."""
        self._show_error("Invalid username or password")
        self.login_btn.configure(state="normal", text="Login")
        self.pass_entry.delete(0, "end")
        self.pass_entry.focus()
    
    def _show_error(self, message: str) -> None:
        """Display an error message."""
        self.error_label.configure(text=f"⚠️ {message}")
    
    def _clear_error(self) -> None:
        """Clear the error message."""
        self.error_label.configure(text="")
