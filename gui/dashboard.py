"""
TriageOS - Dashboard Module (CustomTkinter)
Modern Emergency Room Triage Dashboard with patient queue, vitals monitor, and EKG display.
Uses CustomTkinter for a professional dark-mode appearance.

Features:
- Settings menu with Change Password and Logout
- Mass Casualty Merge for emergency scenarios
- Real-time EKG monitoring
- Patient queue management
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, simpledialog, filedialog
import threading
import time
import random
import math
from typing import Optional, List, Callable

# Import the bridge for backend communication
from bridge import SystemBridge

# Configure CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


# =============================================================================
# COLOR SCHEME
# =============================================================================
COLORS = {
    "bg_dark": "#0f0f1a",
    "bg_card": "#1a1a2e",
    "bg_sidebar": "#16213e",
    "bg_input": "#252545",
    "text": "#ffffff",
    "text_muted": "#a0a0a0",
    "accent": "#00d4ff",
    "accent_hover": "#00a8cc",
    "critical": "#ff4757",
    "critical_dark": "#c0392b",
    "stable": "#00d4ff",
    "success": "#2ed573",
    "warning": "#ffa502",
    "purple": "#9b59b6",
    "purple_hover": "#8e44ad",
    "grid": "#1a1a2e",
}


def get_priority_color(priority: int) -> str:
    """Get color for patient priority. Red for P1-P2 (critical), Cyan for others."""
    if priority <= 2:
        return COLORS["critical"]
    else:
        return COLORS["stable"]


# =============================================================================
# PATIENT VIEW MODEL
# =============================================================================
class PatientViewModel:
    """Stores local state for a patient with simulated vitals and EKG."""
    
    def __init__(self, pid: int, name: str, age: int, priority: int, condition: str):
        self.id = pid
        self.name = name
        self.age = age
        self.priority = int(priority)
        self.condition = condition
        
        # Base vitals based on priority
        self._base_hr = self._calc_base_hr()
        self._base_spo2 = self._calc_base_spo2()
        self._base_bp_sys = self._calc_base_bp_sys()
        self._base_bp_dia = self._calc_base_bp_dia()
        
        # Current vitals
        self.heart_rate = self._base_hr
        self.spo2 = self._base_spo2
        self.bp_sys = self._base_bp_sys
        self.bp_dia = self._base_bp_dia
        
        # EKG waveform data
        self.ekg_data: List[float] = [100.0] * 100
        self.ekg_phase = 0
        self._frame_count = 0
    
    def _calc_base_hr(self) -> int:
        if self.priority == 1: return 135
        elif self.priority <= 3: return 110
        elif self.priority <= 6: return 85
        else: return 72
    
    def _calc_base_spo2(self) -> int:
        if self.priority == 1: return 91
        elif self.priority <= 3: return 94
        else: return 98
    
    def _calc_base_bp_sys(self) -> int:
        if self.priority == 1: return 155
        elif self.priority <= 3: return 135
        else: return 120
    
    def _calc_base_bp_dia(self) -> int:
        if self.priority == 1: return 95
        elif self.priority <= 3: return 88
        else: return 80
    
    def update_vitals(self) -> None:
        """Update vitals with subtle fluctuations."""
        self._frame_count += 1
        
        if self._frame_count >= 20:
            self._frame_count = 0
            jitter = 3 if self.priority == 1 else 2
            self.heart_rate = self._base_hr + random.randint(-jitter, jitter)
            self.spo2 = max(85, min(100, self._base_spo2 + random.randint(-1, 0)))
            self.bp_sys = self._base_bp_sys + random.randint(-2, 2)
            self.bp_dia = self._base_bp_dia + random.randint(-1, 1)
        
        self._update_ekg()
    
    def _update_ekg(self) -> None:
        """Generate realistic EKG waveform."""
        self.ekg_phase += 1
        freq = self.heart_rate / 60
        t = self.ekg_phase * 0.05
        y = 100.0
        phase_in_beat = (t * freq) % 1
        
        if 0.10 < phase_in_beat < 0.16:
            progress = (phase_in_beat - 0.10) / 0.06
            y = 100 - 8 * math.sin(progress * math.pi)
        elif 0.20 < phase_in_beat < 0.22:
            y = 108
        elif 0.22 < phase_in_beat < 0.28:
            progress = (phase_in_beat - 0.22) / 0.06
            spike = 55 if self.priority <= 3 else 50
            y = 100 - spike * math.sin(progress * math.pi)
        elif 0.28 < phase_in_beat < 0.32:
            progress = (phase_in_beat - 0.28) / 0.04
            y = 100 + 12 * (1 - progress)
        elif 0.40 < phase_in_beat < 0.55:
            progress = (phase_in_beat - 0.40) / 0.15
            y = 100 - 12 * math.sin(progress * math.pi)
        
        noise = random.uniform(-1.5, 1.5) if self.priority == 1 else random.uniform(-0.5, 0.5)
        y += noise
        
        self.ekg_data.pop(0)
        self.ekg_data.append(y)


# =============================================================================
# ER DASHBOARD (Main Application)
# =============================================================================
class ERDashboard(ctk.CTk):
    """
    Modern Emergency Room Dashboard using CustomTkinter.
    
    Features:
    - Scrollable patient queue sidebar
    - Real-time EKG monitor with vital signs
    - Quick action buttons for patient management
    - Settings menu with Change Password and Logout
    - Mass Casualty Merge for emergency scenarios
    - Background C++ communication
    """
    
    def __init__(self, bridge: SystemBridge, on_logout_callback: Optional[Callable[[], None]] = None):
        super().__init__()
        
        self.bridge = bridge
        self.on_logout_callback = on_logout_callback
        self.running = True
        self.is_logging_out = False
        
        # Patient data
        self.patients: List[PatientViewModel] = []
        self.selected_patient: Optional[PatientViewModel] = None
        self.patient_count = 0
        self.estimated_wait = 0
        self.pending_extract = False
        
        # Window configuration
        self.title("TRIAGE O.S. - Emergency Room Management")
        self.geometry("1400x850")
        self.minsize(1200, 700)
        self.configure(fg_color=COLORS["bg_dark"])
        
        # Build the UI
        self._create_header()
        self._create_main_layout()
        
        # Start background threads
        self._start_status_monitor()
        self._start_animation_loop()
        self._start_cpp_listener()
        
        # Request initial stats
        self.after(500, lambda: self.bridge.send_command("STATS"))
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_close)
    
    def _create_header(self) -> None:
        """Create the top header bar with settings."""
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=70, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
        # Left: Logo and Title
        left_frame = ctk.CTkFrame(header, fg_color="transparent")
        left_frame.pack(side="left", padx=20, pady=10)
        
        logo = ctk.CTkLabel(left_frame, text="🏥", font=ctk.CTkFont(size=36))
        logo.pack(side="left", padx=(0, 10))
        
        title = ctk.CTkLabel(
            left_frame,
            text="TRIAGE O.S.",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=COLORS["accent"]
        )
        title.pack(side="left")
        
        subtitle = ctk.CTkLabel(
            left_frame,
            text="Emergency Room Management",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        subtitle.pack(side="left", padx=(15, 0))
        
        # Right: Status and Settings
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)
        
        # Settings button (gear icon)
        settings_btn = ctk.CTkButton(
            right_frame,
            text="⚙️",
            font=ctk.CTkFont(size=20),
            width=40,
            height=40,
            corner_radius=20,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_sidebar"],
            command=self._show_settings
        )
        settings_btn.pack(side="right", padx=(10, 0))
        
        # Status label
        self.status_label = ctk.CTkLabel(
            right_frame,
            text="● CONNECTED",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["success"]
        )
        self.status_label.pack(side="right")
    
    def _show_settings(self) -> None:
        """Show the settings popup."""
        settings = ctk.CTkToplevel(self)
        settings.title("Settings")
        settings.geometry("300x200")
        settings.configure(fg_color=COLORS["bg_card"])
        settings.resizable(False, False)
        settings.transient(self)
        settings.grab_set()
        
        # Center on parent
        settings.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 150
        y = self.winfo_y() + (self.winfo_height() // 2) - 100
        settings.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            settings,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=20)
        
        # Change Password button
        ctk.CTkButton(
            settings,
            text="🔑 Change Password",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=10,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            command=lambda: [settings.destroy(), self._show_change_password()]
        ).pack(fill="x", padx=30, pady=(0, 10))
        
        # Logout button
        ctk.CTkButton(
            settings,
            text="🚪 Logout",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=10,
            fg_color=COLORS["critical"],
            hover_color=COLORS["critical_dark"],
            command=lambda: [settings.destroy(), self._on_logout()]
        ).pack(fill="x", padx=30)
    
    def _show_change_password(self) -> None:
        """Show the change password dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Change Password")
        dialog.geometry("350x350")
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        # Center on parent
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 175
        y = self.winfo_y() + (self.winfo_height() // 2) - 175
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            dialog,
            text="🔑 Change Password",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=20)
        
        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="x", padx=30)
        
        ctk.CTkLabel(form, text="Username:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(5, 2))
        user_entry = ctk.CTkEntry(form, height=35, corner_radius=8)
        user_entry.pack(fill="x")
        user_entry.insert(0, "admin")
        
        ctk.CTkLabel(form, text="Current Password:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        old_pass_entry = ctk.CTkEntry(form, height=35, corner_radius=8, show="•")
        old_pass_entry.pack(fill="x")
        
        ctk.CTkLabel(form, text="New Password:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        new_pass_entry = ctk.CTkEntry(form, height=35, corner_radius=8, show="•")
        new_pass_entry.pack(fill="x")
        
        # Store reference to handle response
        self._change_pass_dialog = dialog
        
        def submit():
            user = user_entry.get().strip()
            old_pass = old_pass_entry.get().strip()
            new_pass = new_pass_entry.get().strip()
            
            if not user or not old_pass or not new_pass:
                messagebox.showerror("Error", "All fields are required")
                return
            
            self.bridge.send_command(f"CHANGE_PASS {user} {old_pass} {new_pass}")
        
        ctk.CTkButton(
            dialog,
            text="Change Password",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=40,
            corner_radius=10,
            fg_color=COLORS["success"],
            hover_color="#27ae60",
            command=submit
        ).pack(pady=20)
    
    def _on_logout(self) -> None:
        """Handle logout action."""
        self.is_logging_out = True
        self.running = False
        
        if self.on_logout_callback:
            self.on_logout_callback()
        
        self.destroy()
    
    def _create_main_layout(self) -> None:
        """Create main content with sidebar and monitor."""
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left: Sidebar
        self._create_sidebar(main)
        
        # Right: Controls + Monitor container
        right_container = ctk.CTkFrame(main, fg_color="transparent")
        right_container.pack(side="left", fill="both", expand=True)
        
        # Quick Actions (ABOVE the monitor)
        self._create_controls(right_container)
        
        # Patient Monitor (below the controls)
        self._create_monitor(right_container)
    
    def _create_sidebar(self, parent: ctk.CTkFrame) -> None:
        """Create the patient queue sidebar."""
        sidebar = ctk.CTkFrame(parent, fg_color=COLORS["bg_sidebar"], width=350, corner_radius=15)
        sidebar.pack(side="left", fill="y", padx=(0, 10))
        sidebar.pack_propagate(False)
        
        # Header
        header = ctk.CTkFrame(sidebar, fg_color="transparent")
        header.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            header,
            text="📋 PATIENT QUEUE",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["text"]
        ).pack(side="left")
        
        self.queue_count = ctk.CTkLabel(
            header,
            text="0 patients",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_muted"]
        )
        self.queue_count.pack(side="right")
        
        # Stats bar
        stats = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_dark"], corner_radius=10)
        stats.pack(fill="x", padx=10, pady=(0, 10))
        
        self.wait_label = ctk.CTkLabel(
            stats,
            text="⏱ Est. Wait: 0 min",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["accent"]
        )
        self.wait_label.pack(pady=8)
        
        # Scrollable patient list
        self.queue_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            scrollbar_button_color=COLORS["accent"],
            scrollbar_button_hover_color=COLORS["accent_hover"]
        )
        self.queue_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Placeholder
        self.placeholder = ctk.CTkLabel(
            self.queue_scroll,
            text="No patients in queue\n\nAdd patients using\nthe control panel",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            justify="center"
        )
        self.placeholder.pack(expand=True, pady=50)
    
    def _create_monitor(self, parent: ctk.CTkFrame) -> None:
        """Create the patient monitor area."""
        monitor = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=15)
        monitor.pack(side="left", fill="both", expand=True)
        
        # Header
        header = ctk.CTkFrame(monitor, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            header,
            text="🩺 PATIENT MONITOR",
            font=ctk.CTkFont(size=14, weight="bold")
        ).pack(side="left")
        
        self.patient_name = ctk.CTkLabel(
            header,
            text="",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=COLORS["accent"]
        )
        self.patient_name.pack(side="right")
        
        # EKG Display (using tk.Canvas inside CTkFrame)
        ekg_frame = ctk.CTkFrame(monitor, fg_color=COLORS["bg_dark"], corner_radius=10)
        ekg_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            ekg_frame,
            text="ECG",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["success"]
        ).pack(anchor="w", padx=10, pady=(5, 0))
        
        # Standard tk.Canvas for EKG (CTK doesn't have a canvas widget)
        self.ekg_canvas = tk.Canvas(
            ekg_frame,
            height=140,
            bg="#000000",
            highlightthickness=0
        )
        self.ekg_canvas.pack(fill="x", padx=10, pady=(0, 10))
        
        # Vitals display
        self._create_vitals(monitor)
        
        # Patient info
        info_frame = ctk.CTkFrame(monitor, fg_color=COLORS["bg_dark"], corner_radius=10)
        info_frame.pack(fill="x", padx=20, pady=10)
        
        self.condition_label = ctk.CTkLabel(
            info_frame,
            text="Condition: --",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.condition_label.pack(anchor="w", padx=15, pady=(10, 2))
        
        self.age_label = ctk.CTkLabel(
            info_frame,
            text="Age: --",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"]
        )
        self.age_label.pack(anchor="w", padx=15, pady=(0, 10))
    
    def _create_controls(self, parent: ctk.CTkFrame) -> None:
        """Create action buttons including Mass Casualty."""
        controls = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=15)
        controls.pack(fill="x", pady=(0, 10))
        
        inner = ctk.CTkFrame(controls, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkLabel(
            inner,
            text="⚡ QUICK ACTIONS",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text"]
        ).pack(anchor="w")
        
        btn_frame = ctk.CTkFrame(inner, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(10, 0))
        
        # Button style
        btn_height = 38
        btn_corner = 8
        
        ctk.CTkButton(
            btn_frame,
            text="➕ Add Patient",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#1a1a2e",
            command=self._on_add_patient
        ).pack(side="left", padx=(0, 8))
        
        ctk.CTkButton(
            btn_frame,
            text="🏥 Treat Next",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["success"],
            hover_color="#27ae60",
            text_color="#1a1a2e",
            command=self._on_extract
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            btn_frame,
            text="⚠️ Update Priority",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["warning"],
            hover_color="#e67e22",
            text_color="#1a1a2e",
            command=self._on_update
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            btn_frame,
            text="🚪 Patient Left",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["critical"],
            hover_color=COLORS["critical_dark"],
            text_color="#ffffff",
            command=self._on_leave
        ).pack(side="left", padx=8)
        
        # Mass Casualty button (purple)
        ctk.CTkButton(
            btn_frame,
            text="🚑 Mass Casualty",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["purple"],
            hover_color=COLORS["purple_hover"],
            text_color="#ffffff",
            command=self._on_mass_casualty
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            btn_frame,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["bg_input"],
            hover_color=COLORS["bg_sidebar"],
            text_color="#ffffff",
            command=self._on_refresh
        ).pack(side="right")
    
    def _create_vitals(self, parent: ctk.CTkFrame) -> None:
        """Create vital signs display."""
        vitals = ctk.CTkFrame(parent, fg_color="transparent")
        vitals.pack(fill="x", padx=20, pady=5)
        
        # Create 4 vital sign boxes
        self.hr_value = self._create_vital_box(vitals, "HEART RATE", "--", "BPM", COLORS["success"])
        self.spo2_value = self._create_vital_box(vitals, "SpO2", "--", "%", COLORS["accent"])
        self.bp_value = self._create_vital_box(vitals, "BLOOD PRESSURE", "--/--", "mmHg", COLORS["warning"])
        self.prio_value = self._create_vital_box(vitals, "PRIORITY", "--", "LEVEL", COLORS["critical"])
    
    def _create_vital_box(self, parent, label: str, value: str, unit: str, color: str) -> ctk.CTkLabel:
        """Create a single vital sign display box."""
        box = ctk.CTkFrame(parent, fg_color=COLORS["bg_dark"], corner_radius=10)
        box.pack(side="left", expand=True, fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(
            box,
            text=label,
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", padx=15, pady=(10, 0))
        
        value_label = ctk.CTkLabel(
            box,
            text=value,
            font=ctk.CTkFont(family="Consolas", size=32, weight="bold"),
            text_color=color
        )
        value_label.pack(anchor="w", padx=15)
        
        ctk.CTkLabel(
            box,
            text=unit,
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", padx=15, pady=(0, 10))
        
        return value_label
    
    # =========================================================================
    # BACKGROUND THREADS
    # =========================================================================
    
    def _start_status_monitor(self) -> None:
        """Monitor connection status."""
        def monitor():
            while self.running:
                try:
                    if not self.winfo_exists():
                        break
                    connected = self.bridge.check_alive()
                    self.after(0, lambda c=connected: self._update_status(c))
                except Exception:
                    break
                time.sleep(1)
        
        threading.Thread(target=monitor, daemon=True).start()
    
    def _update_status(self, connected: bool) -> None:
        """Update status indicator."""
        try:
            if not self.winfo_exists():
                return
            if connected:
                self.status_label.configure(text="● CONNECTED", text_color=COLORS["success"])
            else:
                self.status_label.configure(text="● DISCONNECTED", text_color=COLORS["critical"])
        except Exception:
            pass
    
    def _start_animation_loop(self) -> None:
        """Animate vitals and EKG."""
        def animate():
            if not self.running:
                return
            try:
                if not self.winfo_exists():
                    return
                if self.selected_patient:
                    self.selected_patient.update_vitals()
                    self._update_monitor()
                self.after(50, animate)
            except Exception:
                pass
        animate()
    
    def _start_cpp_listener(self) -> None:
        """Listen for C++ backend responses."""
        def listen():
            print("[Dashboard] Listener started")
            while self.running:
                try:
                    line = self.bridge.read_line()
                    if line is None:
                        if not self.running:
                            break
                        time.sleep(0.5)
                        continue
                    if line and self.running:
                        try:
                            if self.winfo_exists():
                                self.after(0, lambda l=line: self._process_response(l))
                        except Exception:
                            break
                except Exception:
                    break
            print("[Dashboard] Listener stopped")
        
        threading.Thread(target=listen, daemon=True).start()
    
    def _process_response(self, line: str) -> None:
        """Handle C++ backend responses."""
        parts = line.split()
        if not parts:
            return
        
        cmd = parts[0]
        
        if cmd == "SUCCESS_ADD":
            name = parts[1] if len(parts) > 1 else "Unknown"
            pid = 0
            for p in parts:
                if p.startswith("ID:"):
                    pid = int(p[3:])
            self.bridge.send_command("STATS")
            messagebox.showinfo("Patient Added", f"{name} added with ID: {pid}")
        
        elif cmd == "DATA":
            if len(parts) >= 6:
                pid, prio, age = int(parts[1]), int(parts[2]), int(parts[3])
                name, desc = parts[4], parts[5]
                
                # Convert underscores back to spaces for display
                display_name = name.replace("_", " ")
                display_desc = desc.replace("_", " ")
                
                if self.pending_extract:
                    self.pending_extract = False
                    
                    # Remove patient - match by ID if known, otherwise by name
                    self.patients = [p for p in self.patients 
                                     if not (p.id == pid or 
                                            (p.id == 0 and (p.name == name or p.name == display_name)))]
                    
                    if self.selected_patient and (self.selected_patient.id == pid or 
                                                   self.selected_patient.name == name or 
                                                   self.selected_patient.name == display_name):
                        self.selected_patient = None
                    
                    self._refresh_sidebar()
                    self._update_monitor()
                    self.bridge.send_command("STATS")
                    self._show_treatment_alert(display_name, pid, prio)
                else:
                    patient = PatientViewModel(pid, name, age, prio, desc)
                    if not any(p.id == pid for p in self.patients):
                        self.patients.append(patient)
                        self._refresh_sidebar()
                    self.selected_patient = patient
                    self._update_monitor()
        
        elif cmd == "EMPTY":
            self.pending_extract = False
            messagebox.showinfo("Empty Queue", "No patients in the queue.")
        
        elif cmd == "STATS":
            for p in parts[1:]:
                if p.startswith("COUNT:"):
                    self.patient_count = int(p[6:])
                elif p.startswith("WAIT:"):
                    self.estimated_wait = int(p[5:])
            self.queue_count.configure(text=f"{self.patient_count} patients")
            self.wait_label.configure(text=f"⏱ Est. Wait: {self.estimated_wait} min")
        
        elif cmd == "SUCCESS_UPDATE":
            messagebox.showinfo("Updated", "Patient priority updated.")
            self.bridge.send_command("STATS")
        
        elif cmd == "SUCCESS_REMOVE":
            pid = int(parts[1]) if len(parts) > 1 else 0
            self.patients = [p for p in self.patients if p.id != pid]
            if self.selected_patient and self.selected_patient.id == pid:
                self.selected_patient = None
            self._refresh_sidebar()
            self.bridge.send_command("STATS")
        
        # Password change responses
        elif cmd == "SUCCESS_PASS_CHANGE":
            if hasattr(self, '_change_pass_dialog') and self._change_pass_dialog:
                self._change_pass_dialog.destroy()
                self._change_pass_dialog = None
            messagebox.showinfo("Success", "Password changed successfully!")
        
        elif cmd == "ERROR_PASS_CHANGE":
            messagebox.showerror("Error", "Failed to change password.\nCheck username and current password.")
        
        # Merge responses
        elif cmd == "SUCCESS_MERGE":
            messagebox.showinfo("Mass Casualty", "Patient data merged successfully!")
            self.bridge.send_command("STATS")
        
        elif cmd == "ERROR_FILE_NOT_FOUND":
            messagebox.showerror("Error", "File not found. Please select a valid file.")
        
        elif cmd.startswith("ERROR"):
            messagebox.showerror("Error", line)
    
    # =========================================================================
    # UI UPDATES
    # =========================================================================
    
    def _refresh_sidebar(self) -> None:
        """Refresh the patient queue."""
        for widget in self.queue_scroll.winfo_children():
            widget.destroy()
        
        if not self.patients:
            self.placeholder = ctk.CTkLabel(
                self.queue_scroll,
                text="No patients in queue\n\nAdd patients using\nthe control panel",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_muted"],
                justify="center"
            )
            self.placeholder.pack(expand=True, pady=50)
            return
        
        for patient in sorted(self.patients, key=lambda p: p.priority):
            self._create_patient_card(patient)
    
    def _create_patient_card(self, patient: PatientViewModel) -> None:
        """Create a patient card in the sidebar."""
        color = get_priority_color(patient.priority)
        
        card = ctk.CTkFrame(
            self.queue_scroll,
            fg_color=COLORS["bg_dark"],
            corner_radius=10,
            border_width=2,
            border_color=color
        )
        card.pack(fill="x", pady=4, padx=5)
        
        # Content
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=8)
        
        # Name
        name_label = ctk.CTkLabel(
            content,
            text=patient.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"]
        )
        name_label.pack(anchor="w")
        
        # Details
        details = ctk.CTkLabel(
            content,
            text=f"ID: {patient.id} | Age: {patient.age} | {patient.condition}",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        details.pack(anchor="w")
        
        # Priority badge
        badge = ctk.CTkLabel(
            card,
            text=f"P{patient.priority}",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=color,
            corner_radius=5,
            width=40,
            height=24,
            text_color=COLORS["bg_dark"] if patient.priority > 2 else COLORS["text"]
        )
        badge.place(relx=1.0, rely=0.5, anchor="e", x=-10)
        
        # Click handler
        def on_click(e, p=patient):
            self.selected_patient = p
            self._update_monitor()
        
        for w in [card, content, name_label, details]:
            w.bind("<Button-1>", on_click)
            w.configure(cursor="hand2")
    
    def _update_monitor(self) -> None:
        """Update the monitor display."""
        if not self.selected_patient:
            self.patient_name.configure(text="")
            self.hr_value.configure(text="--")
            self.spo2_value.configure(text="--")
            self.bp_value.configure(text="--/--")
            self.prio_value.configure(text="--")
            self.condition_label.configure(text="Condition: --")
            self.age_label.configure(text="Age: --")
            return
        
        p = self.selected_patient
        self.patient_name.configure(text=f"ID:{p.id} - {p.name}")
        self.hr_value.configure(text=str(p.heart_rate))
        self.spo2_value.configure(text=str(p.spo2))
        self.bp_value.configure(text=f"{p.bp_sys}/{p.bp_dia}")
        
        prio_color = get_priority_color(p.priority)
        self.prio_value.configure(text=str(p.priority), text_color=prio_color)
        
        self.condition_label.configure(text=f"Condition: {p.condition}")
        self.age_label.configure(text=f"Age: {p.age} years")
        
        self._draw_ekg(p)
    
    def _draw_ekg(self, patient: PatientViewModel) -> None:
        """Draw EKG waveform."""
        self.ekg_canvas.delete("all")
        
        width = self.ekg_canvas.winfo_width()
        height = self.ekg_canvas.winfo_height()
        
        if width < 10 or height < 10:
            return
        
        # Grid
        for i in range(0, width, 20):
            self.ekg_canvas.create_line(i, 0, i, height, fill=COLORS["grid"])
        for i in range(0, height, 20):
            self.ekg_canvas.create_line(0, i, width, i, fill=COLORS["grid"])
        
        # Waveform
        color = get_priority_color(patient.priority)
        points = []
        data_len = len(patient.ekg_data)
        
        for i, value in enumerate(patient.ekg_data):
            x = (i / data_len) * width
            y = height - ((value / 200) * height)
            points.extend([x, y])
        
        if len(points) >= 4:
            self.ekg_canvas.create_line(points, fill=color, width=2, smooth=True)
    
    def _show_treatment_alert(self, name: str, pid: int, priority: int) -> None:
        """Show treatment notification."""
        alert = ctk.CTkToplevel(self)
        alert.title("")
        alert.geometry("400x150")
        alert.configure(fg_color=COLORS["success"])
        alert.resizable(False, False)
        
        # Center
        alert.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 75
        alert.geometry(f"+{x}+{y}")
        
        alert.attributes('-topmost', True)
        
        ctk.CTkLabel(
            alert,
            text="🏥 PATIENT CALLED",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=COLORS["bg_dark"]
        ).pack(pady=(20, 5))
        
        ctk.CTkLabel(
            alert,
            text=name,
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["bg_dark"]
        ).pack()
        
        ctk.CTkLabel(
            alert,
            text=f"ID: {pid} | Priority: {priority}",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["bg_dark"]
        ).pack(pady=(5, 0))
        
        alert.after(2000, alert.destroy)
        alert.bind("<Button-1>", lambda e: alert.destroy())
    
    # =========================================================================
    # COMMAND HANDLERS
    # =========================================================================
    
    def _on_add_patient(self) -> None:
        """Add patient dialog."""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add New Patient")
        dialog.geometry("400x480")
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.resizable(False, False)
        dialog.transient(self)
        dialog.grab_set()
        
        dialog.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() // 2) - 200
        y = self.winfo_y() + (self.winfo_height() // 2) - 240
        dialog.geometry(f"+{x}+{y}")
        
        ctk.CTkLabel(
            dialog,
            text="Add New Patient",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=20)
        
        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="x", padx=30)
        
        # Name field (first)
        ctk.CTkLabel(form, text="Patient Name:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        name_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. John Smith")
        name_entry.pack(fill="x")
        
        # Age field (second)
        ctk.CTkLabel(form, text="Age:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        age_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. 45")
        age_entry.pack(fill="x")
        
        # Priority field (third)
        ctk.CTkLabel(form, text="Priority (1=Critical, 10=Stable):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        prio_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. 3")
        prio_entry.pack(fill="x")
        
        # Description/Condition field (fourth)
        ctk.CTkLabel(form, text="Condition/Description:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        cond_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. Chest Pain")
        cond_entry.pack(fill="x")
        
        def submit():
            try:
                name_input = name_entry.get().strip()
                age = int(age_entry.get().strip())
                prio = int(prio_entry.get().strip())
                cond_input = cond_entry.get().strip()
                
                if not (1 <= prio <= 10):
                    messagebox.showerror("Error", "Priority must be 1-10")
                    return
                if not name_input or not cond_input:
                    messagebox.showerror("Error", "Name and condition required")
                    return
                
                # Replace spaces with underscores for C++ backend
                name_backend = name_input.replace(" ", "_")
                cond_backend = cond_input.replace(" ", "_")
                
                self.bridge.send_command(f"ADD {prio} {age} {name_backend} {cond_backend}")
                
                # Store with display name (spaces preserved for UI)
                new_patient = PatientViewModel(0, name_input, age, prio, cond_input)
                self.patients.append(new_patient)
                self._refresh_sidebar()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Age and Priority must be numbers")
        
        ctk.CTkButton(
            dialog,
            text="Add Patient",
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40,
            corner_radius=10,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            text_color="#1a1a2e",
            command=submit
        ).pack(pady=25)
    
    def _on_extract(self) -> None:
        """Treat next patient."""
        self.pending_extract = True
        self.bridge.send_command("EXTRACT")
    
    def _on_update(self) -> None:
        """Update patient priority."""
        if not self.selected_patient:
            messagebox.showwarning("No Selection", "Select a patient first.")
            return
        
        new_prio = simpledialog.askinteger(
            "Update Priority",
            f"New priority for {self.selected_patient.name}\n(1=Critical, 10=Stable)\nCurrent: {self.selected_patient.priority}",
            minvalue=1, maxvalue=10, parent=self
        )
        
        if new_prio:
            if new_prio >= self.selected_patient.priority:
                messagebox.showwarning("Invalid", "Can only decrease priority (more urgent).")
                return
            self.bridge.send_command(f"UPDATE {self.selected_patient.id} {new_prio}")
            self.selected_patient.priority = new_prio
            self._refresh_sidebar()
    
    def _on_leave(self) -> None:
        """Remove patient who left."""
        if not self.selected_patient:
            messagebox.showwarning("No Selection", "Select a patient first.")
            return
        
        if messagebox.askyesno("Confirm", f"Remove {self.selected_patient.name}?"):
            self.bridge.send_command(f"LEAVE {self.selected_patient.id}")
    
    def _on_mass_casualty(self) -> None:
        """Handle mass casualty merge - import patients from file."""
        filename = filedialog.askopenfilename(
            title="Select Patient Data File",
            filetypes=[
                ("Text files", "*.txt"),
                ("All files", "*.*")
            ],
            parent=self
        )
        
        if filename:
            self.bridge.send_command(f"MERGE {filename}")
    
    def _on_refresh(self) -> None:
        """Refresh stats."""
        self.bridge.send_command("STATS")
    
    def _on_close(self) -> None:
        """Handle window close (X button)."""
        self.running = False
        
        # Only close bridge if not logging out (logout keeps looping)
        if not self.is_logging_out:
            self.bridge.close()
        
        self.destroy()
