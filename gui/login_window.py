"""
TriageOS - Login Frame Module (CustomTkinter)
Modern authentication GUI for the medical triage system.
Uses CustomTkinter for a professional dark-mode appearance.

ARCHITECTURE:
    This is a Frame (ctk.CTkFrame), not a Window.
    It is designed to be embedded in 'main.py'.
"""

import customtkinter as ctk
from tkinter import messagebox
import threading
from typing import Callable, Optional

# Import the bridge for backend communication
from bridge import SystemBridge

class LoginFrame(ctk.CTkFrame):
    """
    Modern authentication frame for TriageOS.
    
    Features:
    - Centered "Card" layout (Responsive)
    - Thread-safe C++ communication
    - Robust cleanup handling
    """
    
    # Color scheme
    COLORS = {
        "bg_dark": "#1a1a2e",    # Deep Navy
        "bg_card": "#16213e",    # Lighter Navy
        "accent": "#00d4ff",     # Cyan
        "accent_hover": "#00a8cc",
        "text": "#ffffff",
        "text_muted": "#a0a0a0",
        "error": "#ff4757",      # Red
        "success": "#2ed573",    # Green
    }
    
    def __init__(self, master, bridge: SystemBridge, on_success_callback: Callable[[], None]):
        """
        Initialize the login frame.
        
        Args:
            master: Parent window (TriageApp)
            bridge: SystemBridge instance
            on_success_callback: Function to run on login success
        """
        super().__init__(master, fg_color=self.COLORS["bg_dark"])
        
        self.bridge = bridge
        self.on_success_callback = on_success_callback
        
        # Thread control flags
        self.running = True
        self.is_logged_in = False
        
        # Pack self to fill the parent window
        self.pack(fill="both", expand=True)
        
        # Build UI
        self._create_ui()
        
        # Start background listener
        self._start_listener()
        
        # Auto-focus username field
        self.after(100, lambda: self.user_entry.focus())
    
    def _create_ui(self) -> None:
        """Create the centered login card and widgets."""
        
        # === Centered Login Card ===
        self.card = ctk.CTkFrame(
            self,
            fg_color=self.COLORS["bg_card"],
            corner_radius=20,
            width=380,
            height=520
        )
        # Perfectly center the card regardless of window size
        self.card.place(relx=0.5, rely=0.5, anchor="center")
        self.card.pack_propagate(False)  # Force fixed size
        
        # === Logo & Title ===
        ctk.CTkLabel(
            self.card,
            text="🏥",
            font=ctk.CTkFont(size=60)
        ).pack(pady=(35, 10))
        
        ctk.CTkLabel(
            self.card,
            text="TRIAGE O.S.",
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=self.COLORS["accent"]
        ).pack(pady=(0, 5))
        
        ctk.CTkLabel(
            self.card,
            text="Emergency Room Management System",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["text_muted"]
        ).pack(pady=(0, 30))
        
        # === Form Container ===
        form = ctk.CTkFrame(self.card, fg_color="transparent")
        form.pack(fill="x", padx=35)
        
        # Username
        self.user_entry = ctk.CTkEntry(
            form,
            placeholder_text="Username",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            border_width=2,
            border_color=self.COLORS["accent"]
        )
        self.user_entry.pack(fill="x", pady=(0, 15))
        
        # Password
        self.pass_entry = ctk.CTkEntry(
            form,
            placeholder_text="Password",
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            border_width=2,
            border_color=self.COLORS["accent"],
            show="•"
        )
        self.pass_entry.pack(fill="x", pady=(0, 15))
        
        # Error Label
        self.error_label = ctk.CTkLabel(
            form,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=self.COLORS["error"]
        )
        self.error_label.pack(pady=(0, 10))
        
        # Login Button
        self.login_btn = ctk.CTkButton(
            form,
            text="Login",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=50,
            corner_radius=10,
            fg_color=self.COLORS["accent"],
            hover_color=self.COLORS["accent_hover"],
            command=self._attempt_login
        )
        self.login_btn.pack(fill="x", pady=(5, 0))
        
        # Footer
        ctk.CTkLabel(
            self.card,
            text="Secure Medical Triage Platform",
            font=ctk.CTkFont(size=10),
            text_color=self.COLORS["text_muted"]
        ).pack(side="bottom", pady=25)
        
        # === Event Bindings ===
        # Bind Enter key specifically to fields (Safe)
        self.user_entry.bind("<Return>", lambda e: self._attempt_login())
        self.pass_entry.bind("<Return>", lambda e: self._attempt_login())
    
    def _attempt_login(self) -> None:
        """Validate input and send login command."""
        user = self.user_entry.get().strip()
        pwd = self.pass_entry.get().strip()
        
        if not user:
            self._show_error("Please enter a username")
            self.user_entry.focus()
            return
        if not pwd:
            self._show_error("Please enter a password")
            self.pass_entry.focus()
            return
            
        self.login_btn.configure(state="disabled", text="Authenticating...")
        self._clear_error()
        
        # Send to C++ Backend
        if not self.bridge.send_command(f"LOGIN {user} {pwd}"):
            self._show_error("Backend Connection Failed")
            self.login_btn.configure(state="normal", text="Login")

    def _start_listener(self) -> None:
        """Start thread to listen for C++ login response."""
        def listen():
            while self.running and not self.is_logged_in:
                try:
                    # If frame destroyed, stop listening
                    if not self.winfo_exists():
                        break
                        
                    line = self.bridge.read_line()
                    if not line:
                        continue
                        
                    if line == "SUCCESS_LOGIN":
                        self.is_logged_in = True
                        self.after(0, self._on_login_success)
                        break
                    elif line == "ERROR_LOGIN":
                        self.after(0, self._on_login_failed)
                        
                except Exception:
                    break
                    
        threading.Thread(target=listen, daemon=True).start()
    
    def _on_login_success(self) -> None:
        """Trigger transition to Dashboard."""
        self.on_success_callback()
    
    def _on_login_failed(self) -> None:
        """Reset UI on failure."""
        self._show_error("Invalid Credentials")
        self.login_btn.configure(state="normal", text="Login")
        self.pass_entry.delete(0, "end")
        self.pass_entry.focus()
    
    def _show_error(self, msg: str) -> None:
        self.error_label.configure(text=f"⚠️ {msg}")
        
    def _clear_error(self) -> None:
        self.error_label.configure(text="")
        
    def cleanup(self) -> None:
        """
        Robust cleanup method called by main.py before switching views.
        Stops threads ensures no hanging processes.
        """
        self.running = False