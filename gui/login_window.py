"""
TriageOS - Login Frame Module (CustomTkinter)
Modern authentication GUI for the medical triage system.
Uses CustomTkinter for a professional dark-mode appearance.

ARCHITECTURE:
    This is a Frame (ctk.CTkFrame), not a Window.
    It is designed to be embedded in 'main.py'.
"""

import customtkinter as ctk
import threading
from typing import Callable

# Import the bridge for backend communication
from bridge import SystemBridge
from theme import COLORS

class LoginFrame(ctk.CTkFrame):
    """
    Modern authentication frame for TriageOS.
    
    Features:
    - Centered "Card" layout (Responsive)
    - Thread-safe C++ communication
    - Robust cleanup handling
    """
    
    def __init__(self, master, bridge: SystemBridge, on_success_callback: Callable[[], None]):
        """
        Initialize the login frame.
        
        Args:
            master: Parent window (TriageApp)
            bridge: SystemBridge instance
            on_success_callback: Function to run on login success
        """
        super().__init__(master, fg_color=COLORS["bg_dark"])
        
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
        
        # FLUSH ZOMBIE THREADS:
        # Send a PING to force the old Dashboard listener (if active) to read a line,
        # realize it should stop, and release the pipe for us.
        self.bridge.send_command("PING")
        
        # Auto-focus username field
        self.after(100, lambda: self.user_entry.focus())
    
    def _create_ui(self) -> None:
        """Create the centered login card with high-contrast styling."""
        
        # === Centered Login Card ===
        self.card = ctk.CTkFrame(
            self,
            fg_color=COLORS["bg_card"],
            corner_radius=20,
            width=440,
            height=540
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
            text="SYSTEM LOGIN",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=(0, 5))
        
        ctk.CTkLabel(
            self.card,
            text="TRIAGE O.S. - Emergency Room Management",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        ).pack(pady=(0, 30))
        
        # === Form Container ===
        form = ctk.CTkFrame(self.card, fg_color="transparent")
        form.pack(fill="x", padx=30)
        
        # Username label
        ctk.CTkLabel(
            form,
            text="Username:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", pady=(0, 4))
        
        # Username input - High contrast styling
        self.user_entry = ctk.CTkEntry(
            form,
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            fg_color=COLORS["bg_input"],
            text_color="#ffffff",
            border_width=2,
            border_color=COLORS["accent"],
            placeholder_text="Enter username",
            placeholder_text_color=COLORS["text_muted"]
        )
        self.user_entry.pack(fill="x", pady=(0, 15))
        
        # Password label
        ctk.CTkLabel(
            form,
            text="Password:",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w", pady=(0, 4))
        
        # Password input - High contrast styling
        self.pass_entry = ctk.CTkEntry(
            form,
            font=ctk.CTkFont(size=14),
            height=45,
            corner_radius=10,
            fg_color=COLORS["bg_input"],
            text_color="#ffffff",
            border_width=2,
            border_color=COLORS["accent"],
            placeholder_text="Enter password",
            placeholder_text_color=COLORS["text_muted"],
            show="•"
        )
        self.pass_entry.pack(fill="x", pady=(0, 12))
        
        # Error Label
        self.error_label = ctk.CTkLabel(
            form,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["error"]
        )
        self.error_label.pack(pady=(0, 8))
        
        # Login Button - Dark text on cyan for high contrast
        self.login_btn = ctk.CTkButton(
            form,
            text="🔐 Login",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=50,
            corner_radius=6,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#0a0a14",  # Dark navy text for high contrast
            text_color_disabled="#ffffff",  # White text when disabled
            command=self._attempt_login
        )
        self.login_btn.pack(fill="x", pady=(5, 0))
        
        # Footer
        ctk.CTkLabel(
            self.card,
            text="Secure Medical Triage Platform",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
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
            
        self.login_btn.configure(state="disabled", text="Authenticating...", text_color="#ffffff")
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
