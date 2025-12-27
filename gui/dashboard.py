"""
TriageOS - Dashboard Module (CustomTkinter)
Modern Emergency Room Triage Dashboard with patient queue, vitals monitor, and EKG display.
Uses CustomTkinter for a professional dark-mode appearance.

FIXED VERSION:
- Solved 'application has been destroyed' by parenting popups to winfo_toplevel()
- Added robust existence checks before UI updates
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import threading
import time
import random
import math
from typing import Optional, List, Callable

# Import the bridge for backend communication
from bridge import SystemBridge
from sound_manager import SoundEngine

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
# PATIENT VIEW MODEL (Realistic Medical Simulation)
# =============================================================================
class PatientViewModel:
    """
    Stores local state for a patient with realistic simulated vitals and EKG.
    """
    
    # EKG Wave Parameters
    EKG_WAVES = {
        'P': {'amp': -12, 'pos': 0.12, 'width': 0.025},
        'Q': {'amp': 8, 'pos': 0.20, 'width': 0.008},
        'R': {'amp': -80, 'pos': 0.23, 'width': 0.012},
        'S': {'amp': 18, 'pos': 0.27, 'width': 0.010},
        'T': {'amp': -25, 'pos': 0.42, 'width': 0.045},
    }
    
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
        
        # Current vitals with drift state
        self.heart_rate = self._base_hr
        self.spo2 = self._base_spo2
        self.bp_sys = self._base_bp_sys
        self.bp_dia = self._base_bp_dia
        
        # Drift velocities
        self._hr_drift = 0.0
        self._spo2_drift = 0.0
        self._bp_sys_drift = 0.0
        self._bp_dia_drift = 0.0
        
        # EKG buffer (200 points for lower CPU usage)
        self.ekg_data: List[float] = [100.0] * 200
        self._ekg_time = 0.0
        self._frame_count = 0
        
        # Heart Rate Variability state
        self._rsa_phase = random.uniform(0, 2 * math.pi)
        self._rsa_frequency = 0.25
        self._arrhythmia_factor = 0.15 if self.priority == 1 else 0.0
        self._beat_triggered = False
        self.beat_event = False  # Flag for dashboard to play heartbeat
    
    def _calc_base_hr(self) -> int:
        if self.priority == 1: return 110
        elif self.priority <= 3: return 100
        elif self.priority <= 6: return 80
        else: return 70
    
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
    
    def _gaussian(self, x: float, amp: float, mu: float, sigma: float) -> float:
        return amp * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))
    
    def _get_hrv_heart_rate(self) -> float:
        rsa_amplitude = 5.0 if self.priority > 2 else 3.0
        rsa_component = rsa_amplitude * math.sin(self._rsa_phase)
        arrhythmia = 0.0
        if self._arrhythmia_factor > 0:
            arrhythmia = random.gauss(0, self._base_hr * self._arrhythmia_factor)
        return self._base_hr + self._hr_drift + rsa_component + arrhythmia
    
    def update_vitals(self) -> None:
        self._frame_count += 1
        self._rsa_phase += 2 * math.pi * self._rsa_frequency * 0.05
        
        if self._frame_count >= 10:
            self._frame_count = 0
            self._update_vitals_drift()
        
        points_per_frame = 2
        for _ in range(points_per_frame):
            self._generate_ekg_point()
    
    def _update_vitals_drift(self) -> None:
        drift_strength = 0.3 if self.priority == 1 else 0.15
        
        self._hr_drift += random.gauss(0, drift_strength * 2)
        self._spo2_drift += random.gauss(0, drift_strength * 0.3)
        self._bp_sys_drift += random.gauss(0, drift_strength)
        self._bp_dia_drift += random.gauss(0, drift_strength * 0.5)
        
        damping = 0.9
        self._hr_drift *= damping
        self._spo2_drift *= damping
        self._bp_sys_drift *= damping
        self._bp_dia_drift *= damping
        
        self._hr_drift = max(-8, min(8, self._hr_drift))
        self._spo2_drift = max(-3, min(1, self._spo2_drift))
        self._bp_sys_drift = max(-8, min(8, self._bp_sys_drift))
        self._bp_dia_drift = max(-5, min(5, self._bp_dia_drift))
        
        self.heart_rate = int(self._base_hr + self._hr_drift + 3 * math.sin(self._rsa_phase))
        self.spo2 = int(max(85, min(100, self._base_spo2 + self._spo2_drift)))
        self.bp_sys = int(self._base_bp_sys + self._bp_sys_drift)
        self.bp_dia = int(self._base_bp_dia + self._bp_dia_drift)
    
    def _generate_ekg_point(self) -> None:
        dt = 0.012
        self._ekg_time += dt
        
        current_hr = self._get_hrv_heart_rate()
        beat_duration = 60.0 / current_hr
        
        phase = (self._ekg_time % beat_duration) / beat_duration
        
        # Heartbeat flag (dashboard handles actual sound)
        if self.priority != 1:
            if 0.22 < phase < 0.28 and not self._beat_triggered:
                self.beat_event = True  # Signal dashboard to play sound
                self._beat_triggered = True
            elif phase >= 0.28 or phase < 0.22:
                self._beat_triggered = False
        
        y = 100.0
        for wave_name, params in self.EKG_WAVES.items():
            amp = params['amp']
            pos = params['pos']
            width = params['width']
            if wave_name == 'R' and self.priority <= 2:
                amp *= 1.15
            y += self._gaussian(phase, amp, pos, width)
        
        noise_level = 1.5 if self.priority == 1 else 0.5
        y += random.gauss(0, noise_level)
        y = max(30, min(170, y))
        
        self.ekg_data.pop(0)
        self.ekg_data.append(y)


# =============================================================================
# DASHBOARD FRAME
# =============================================================================
class DashboardFrame(ctk.CTkFrame):
    """
    Modern Emergency Room Dashboard using CustomTkinter.
    """
    
    def __init__(self, master, bridge: SystemBridge, on_logout_callback: Optional[Callable[[], None]] = None):
        super().__init__(master, fg_color=COLORS["bg_dark"])
        
        self.bridge = bridge
        self.on_logout_callback = on_logout_callback
        self.running = True
        self.is_logging_out = False
        
        self.patients: List[PatientViewModel] = []
        self.selected_patient: Optional[PatientViewModel] = None
        self.patient_count = 0
        self.estimated_wait = 0
        self.pending_extract = False
        
        self.sound_engine = SoundEngine()
        self._alarm_playing = False
        
        self.pack(fill="both", expand=True)
        
        self._create_header()
        self._create_main_layout()
        
        self._start_status_monitor()
        self._start_animation_loop()
        self._start_cpp_listener()
        self._start_simulation_loop()
        
        # Use 'after' with safe checks
        self.after(500, self._safe_send_stats)
        self.after(600, self._safe_send_list)

    def _safe_send_stats(self):
        if self.running and self.winfo_exists():
            self.bridge.send_command("STATS")

    def _safe_send_list(self):
        if self.running and self.winfo_exists():
            self.bridge.send_command("LIST")
    
    def _create_header(self) -> None:
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_card"], height=70, corner_radius=0)
        header.pack(fill="x", side="top")
        header.pack_propagate(False)
        
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
        
        right_frame = ctk.CTkFrame(header, fg_color="transparent")
        right_frame.pack(side="right", padx=20, pady=10)
        
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
        
        self.status_label = ctk.CTkLabel(
            right_frame,
            text="● CONNECTED",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["success"]
        )
        self.status_label.pack(side="right")
    
    def _show_settings(self) -> None:
        if not self.winfo_exists(): return
        
        # FIX: Use winfo_toplevel() as master
        settings = ctk.CTkToplevel(self.winfo_toplevel())
        settings.title("Settings")
        settings.geometry("300x200")
        settings.configure(fg_color=COLORS["bg_card"])
        settings.resizable(False, False)
        settings.transient(self.winfo_toplevel())
        settings.grab_set()
        
        settings.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 150
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 100
            settings.geometry(f"+{x}+{y}")
        except:
            pass
        
        ctk.CTkLabel(
            settings,
            text="⚙️ Settings",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=COLORS["accent"]
        ).pack(pady=20)
        
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
        if not self.winfo_exists(): return
        
        # FIX: Use winfo_toplevel() as master
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Change Password")
        dialog.geometry("350x350")
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 175
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 175
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
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
        
        # Don't destroy self here; main.py handles it
        # self.destroy() 
    
    def _create_main_layout(self) -> None:
        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=10, pady=10)
        
        main.grid_columnconfigure(0, weight=0, minsize=300)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)
        
        self._create_sidebar(main)
        
        right_container = ctk.CTkFrame(main, fg_color="transparent")
        right_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        self._create_controls(right_container)
        self._create_monitor(right_container)
    
    def _create_sidebar(self, parent: ctk.CTkFrame) -> None:
        sidebar = ctk.CTkFrame(parent, fg_color=COLORS["bg_sidebar"], width=300, corner_radius=15)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        
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
        
        stats = ctk.CTkFrame(sidebar, fg_color=COLORS["bg_dark"], corner_radius=10)
        stats.pack(fill="x", padx=10, pady=(0, 10))
        
        self.wait_label = ctk.CTkLabel(
            stats,
            text="⏱ Est. Wait: 0 min",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["accent"]
        )
        self.wait_label.pack(pady=8)
        
        self.queue_scroll = ctk.CTkScrollableFrame(
            sidebar,
            fg_color="transparent",
            width=280,
            scrollbar_button_color=COLORS["accent"],
            scrollbar_button_hover_color=COLORS["accent_hover"]
        )
        self.queue_scroll.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.placeholder = ctk.CTkLabel(
            self.queue_scroll,
            text="No patients in queue\n\nAdd patients using\nthe control panel",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_muted"],
            justify="center"
        )
        self.placeholder.pack(expand=True, pady=50)
    
    def _create_monitor(self, parent: ctk.CTkFrame) -> None:
        monitor = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=15)
        monitor.pack(side="left", fill="both", expand=True)
        
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
        
        ekg_frame = ctk.CTkFrame(monitor, fg_color=COLORS["bg_dark"], corner_radius=10)
        ekg_frame.pack(fill="x", padx=20, pady=10)
        
        ctk.CTkLabel(
            ekg_frame,
            text="EKG",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["success"]
        ).pack(anchor="w", padx=10, pady=(5, 0))
        
        self.ekg_canvas = tk.Canvas(
            ekg_frame,
            height=140,
            bg="#000000",
            highlightthickness=0
        )
        self.ekg_canvas.pack(fill="x", padx=10, pady=(0, 10))
        self.ekg_canvas.bind("<Configure>", self._on_ekg_resize)
        
        self._create_vitals(monitor)
        
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
            text="✅ Treated",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["success"],
            hover_color="#27ae60",
            text_color="#1a1a2e",
            command=self._on_treated
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
            text_color="#1a1a2e",
            command=self._on_leave
        ).pack(side="left", padx=8)
        
        ctk.CTkButton(
            btn_frame,
            text="🚑 Mass Casualty",
            font=ctk.CTkFont(size=12, weight="bold"),
            height=btn_height,
            corner_radius=btn_corner,
            fg_color=COLORS["purple"],
            hover_color=COLORS["purple_hover"],
            text_color="#1a1a2e",
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
        vitals = ctk.CTkFrame(parent, fg_color="transparent")
        vitals.pack(fill="x", padx=20, pady=5)
        
        self.hr_value = self._create_vital_box(vitals, "HEART RATE", "--", "BPM", COLORS["success"])
        self.spo2_value = self._create_vital_box(vitals, "SpO2", "--", "%", COLORS["accent"])
        self.bp_value = self._create_vital_box(vitals, "BLOOD PRESSURE", "--/--", "mmHg", COLORS["warning"])
        self.prio_value = self._create_vital_box(vitals, "PRIORITY", "--", "LEVEL", COLORS["critical"])
    
    def _create_vital_box(self, parent, label: str, value: str, unit: str, color: str) -> ctk.CTkLabel:
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
    # THREADS
    # =========================================================================
    
    def _start_status_monitor(self) -> None:
        def monitor():
            while self.running:
                try:
                    if not self.winfo_exists(): break
                    connected = self.bridge.check_alive()
                    self.after(0, lambda c=connected: self._update_status(c))
                except Exception:
                    break
                time.sleep(1)
        threading.Thread(target=monitor, daemon=True).start()
    
    def _update_status(self, connected: bool) -> None:
        if not self.running or not self.winfo_exists(): return
        try:
            if connected:
                self.status_label.configure(text="● CONNECTED", text_color=COLORS["success"])
            else:
                self.status_label.configure(text="● DISCONNECTED", text_color=COLORS["critical"])
        except: pass
    
    def _start_animation_loop(self) -> None:
        def animate():
            if not self.running: return
            try:
                if self.winfo_exists():
                    if self.selected_patient:
                        self.selected_patient.update_vitals()
                        
                        # Play heartbeat on main thread (not from PatientViewModel)
                        if self.selected_patient.beat_event:
                            if self.selected_patient.priority != 1:
                                self.sound_engine.play_heartbeat_if_ready()
                            self.selected_patient.beat_event = False
                        
                        self._update_monitor()
                    self.after(50, animate)
            except Exception:
                pass
        animate()
    
    def _start_cpp_listener(self) -> None:
        def listen():
            while self.running:
                try:
                    line = self.bridge.read_line()
                    if line is None:
                        if not self.running: break
                        time.sleep(0.5)
                        continue
                    if line and self.running:
                        self.after(0, lambda l=line: self._process_response(l))
                except Exception:
                    break
        threading.Thread(target=listen, daemon=True).start()
    
    def _start_simulation_loop(self) -> None:
        def simulate():
            while self.running:
                try:
                    wait_time = random.randint(15, 45)
                    for _ in range(wait_time * 2):
                        if not self.running: return
                        time.sleep(0.5)
                    
                    if not self.running: return
                    
                    stable_patients = [p for p in self.patients if p.priority > 1]
                    if stable_patients:
                        patient = random.choice(stable_patients)
                        patient.priority = 1
                        
                        self.after(0, lambda pid=patient.id: self.bridge.send_command(f"UPDATE {pid} 1"))
                        self.after(0, lambda name=patient.name: self._show_deterioration_alert(name))
                        self.after(100, self._refresh_sidebar)
                except Exception:
                    if not self.running: return
        threading.Thread(target=simulate, daemon=True).start()
    
    def _show_deterioration_alert(self, patient_name: str) -> None:
        if not self.winfo_exists(): return
        
        # FIX: Use winfo_toplevel()
        alert = ctk.CTkToplevel(self.winfo_toplevel())
        alert.title("")
        alert.geometry("400x150")
        alert.configure(fg_color=COLORS["critical"])
        alert.resizable(False, False)
        alert.attributes("-topmost", True)
        
        try:
            alert.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
            y = self.winfo_rooty() + 50
            alert.geometry(f"+{x}+{y}")
        except:
            pass
        
        ctk.CTkLabel(
            alert,
            text="⚠️ CRITICAL ALERT ⚠️",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color="#ffffff"
        ).pack(pady=(20, 10))
        
        ctk.CTkLabel(
            alert,
            text=f"Patient {patient_name} condition deteriorated!",
            font=ctk.CTkFont(size=16),
            text_color="#ffffff"
        ).pack(pady=5)
        
        ctk.CTkLabel(
            alert,
            text="Now PRIORITY 1 - Immediate attention required",
            font=ctk.CTkFont(size=12),
            text_color="#ffcccc"
        ).pack(pady=5)
        
        alert.after(5000, alert.destroy)
    
    def _process_response(self, line: str) -> None:
        if not self.running or not self.winfo_exists(): return
        
        parts = line.split()
        if not parts: return
        cmd = parts[0]
        
        if cmd == "SUCCESS_ADD":
            name = parts[1] if len(parts) > 1 else "Unknown"
            pid = 0
            for p in parts:
                if p.startswith("ID:"):
                    pid = int(p[3:])
            
            display_name = name.replace("_", " ")
            for patient in self.patients:
                if patient.id == 0 and (patient.name == name or patient.name == display_name):
                    patient.id = pid
                    break
            
            self._refresh_sidebar()
            self.bridge.send_command("STATS")
            messagebox.showinfo("Patient Added", f"{display_name} added with ID: {pid}")
        
        elif cmd == "DATA":
            if len(parts) >= 6:
                pid, prio, age = int(parts[1]), int(parts[2]), int(parts[3])
                name, desc = parts[4], parts[5]
                
                display_name = name.replace("_", " ")
                display_desc = desc.replace("_", " ")
                
                if self.pending_extract:
                    self.pending_extract = False
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
                    self.bridge.send_command("LIST")
                    
                    diagnosis = getattr(self, 'current_diagnosis', '')
                    self._show_treatment_alert(display_name, pid, prio, diagnosis)
                    self.current_diagnosis = None
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
        
        elif cmd == "LIST_DATA":
            if len(parts) >= 6:
                pid, prio, age = int(parts[1]), int(parts[2]), int(parts[3])
                name, desc = parts[4], parts[5]
                display_name = name.replace("_", " ")
                display_desc = desc.replace("_", " ")
                
                if not any(p.id == pid for p in self.patients):
                    patient = PatientViewModel(pid, display_name, age, prio, display_desc)
                    self.patients.append(patient)
                    self._refresh_sidebar()
        
        elif cmd == "SUCCESS_UPDATE":
            messagebox.showinfo("Updated", "Patient priority updated.")
            self.bridge.send_command("STATS")
        
        elif cmd == "SUCCESS_REMOVE":
            pid = int(parts[1]) if len(parts) > 1 else 0
            self.patients = [p for p in self.patients if p.id != pid]
            if self.selected_patient and self.selected_patient.id == pid:
                self.selected_patient = None
            self._refresh_sidebar()
            self._update_monitor()
            self.bridge.send_command("STATS")
        
        elif cmd == "SUCCESS_PASS_CHANGE":
            if hasattr(self, '_change_pass_dialog') and self._change_pass_dialog:
                self._change_pass_dialog.destroy()
                self._change_pass_dialog = None
            messagebox.showinfo("Success", "Password changed successfully!")
        
        elif cmd == "ERROR_PASS_CHANGE":
            messagebox.showerror("Error", "Failed to change password.\nCheck username and current password.")
        
        elif cmd == "SUCCESS_MERGE":
            messagebox.showinfo("Mass Casualty", "Patient data merged successfully!")
            self.bridge.send_command("STATS")
            self.bridge.send_command("LIST")
        
        elif cmd == "ERROR_FILE_NOT_FOUND":
            messagebox.showerror("Error", "File not found. Please select a valid file.")
        
        elif cmd.startswith("ERROR"):
            messagebox.showerror("Error", line)
    
    def _refresh_sidebar(self) -> None:
        if not self.winfo_exists(): return
        
        count = len(self.patients)
        self.queue_count.configure(text=f"{count} patients")
        
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
        color = get_priority_color(patient.priority)
        
        card = ctk.CTkFrame(
            self.queue_scroll,
            fg_color=COLORS["bg_dark"],
            corner_radius=10,
            border_width=2,
            border_color=color
        )
        card.pack(fill="x", pady=4, padx=5)
        
        content = ctk.CTkFrame(card, fg_color="transparent")
        content.pack(fill="x", padx=10, pady=8)
        
        name_label = ctk.CTkLabel(
            content,
            text=patient.name,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=COLORS["text"]
        )
        name_label.pack(anchor="w")
        
        details = ctk.CTkLabel(
            content,
            text=f"ID: {patient.id} | Age: {patient.age} | {patient.condition}",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_muted"]
        )
        details.pack(anchor="w")
        
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
        
        def on_click(e, p=patient):
            self.selected_patient = p
            self._update_monitor()
        
        for w in [card, content, name_label, details]:
            w.bind("<Button-1>", on_click)
            w.configure(cursor="hand2")
    
    def _update_monitor(self) -> None:
        if not self.running or not self.winfo_exists(): return
        
        if not self.selected_patient:
            self.patient_name.configure(text="")
            self.hr_value.configure(text="--")
            self.spo2_value.configure(text="--")
            self.bp_value.configure(text="--/--")
            self.prio_value.configure(text="--")
            self.condition_label.configure(text="Condition: --")
            self.age_label.configure(text="Age: --")
            if self._alarm_playing:
                self.sound_engine.stop_alarm()
                self._alarm_playing = False
            self._reset_ekg()
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
        
        if p.priority == 1:
            if not self._alarm_playing:
                self.sound_engine.play_alarm()
                self._alarm_playing = True
        else:
            if self._alarm_playing:
                self.sound_engine.stop_alarm()
                self._alarm_playing = False
        
        self._draw_ekg(p)
    
    def _draw_ekg(self, patient: PatientViewModel) -> None:
        self.ekg_canvas.delete("ekg_line")
        width = self.ekg_canvas.winfo_width()
        height = self.ekg_canvas.winfo_height()
        if width < 10 or height < 10: return
        
        color = get_priority_color(patient.priority)
        points = []
        data_len = len(patient.ekg_data)
        for i, value in enumerate(patient.ekg_data):
            x = (i / data_len) * width
            y = height - ((value / 200) * height)
            points.extend([x, y])
        
        if len(points) >= 4:
            self.ekg_canvas.create_line(points, fill=color, width=2, smooth=False, tags="ekg_line")
    
    def _on_ekg_resize(self, event=None) -> None:
        self.ekg_canvas.delete("grid")
        width = self.ekg_canvas.winfo_width()
        height = self.ekg_canvas.winfo_height()
        if width < 10 or height < 10: return
        
        for i in range(0, width, 20):
            self.ekg_canvas.create_line(i, 0, i, height, fill=COLORS["grid"], tags="grid")
        for i in range(0, height, 20):
            self.ekg_canvas.create_line(0, i, width, i, fill=COLORS["grid"], tags="grid")
    
    def _reset_ekg(self) -> None:
        self.ekg_canvas.delete("ekg_line")
    
    def _show_treatment_alert(self, name: str, pid: int, priority: int, diagnosis: str = "") -> None:
        if not self.winfo_exists(): return
        
        # FIX: Use winfo_toplevel()
        alert = ctk.CTkToplevel(self.winfo_toplevel())
        alert.title("")
        alert.geometry("450x200")
        alert.configure(fg_color=COLORS["success"])
        alert.resizable(False, False)
        
        try:
            alert.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 225
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 100
            alert.geometry(f"+{x}+{y}")
        except:
            pass
        
        alert.attributes('-topmost', True)
        
        ctk.CTkLabel(alert, text="✅ PATIENT DISCHARGED", font=ctk.CTkFont(size=14, weight="bold"), text_color=COLORS["bg_dark"]).pack(pady=(20, 5))
        ctk.CTkLabel(alert, text=name, font=ctk.CTkFont(size=22, weight="bold"), text_color=COLORS["bg_dark"]).pack()
        ctk.CTkLabel(alert, text=f"ID: {pid} | Priority: {priority}", font=ctk.CTkFont(size=12), text_color=COLORS["bg_dark"]).pack(pady=(5, 0))
        
        if diagnosis:
            ctk.CTkLabel(alert, text=f"Diagnosis: {diagnosis}", font=ctk.CTkFont(size=12, slant="italic"), text_color=COLORS["bg_dark"], wraplength=400).pack(pady=(10, 0))
        
        alert.after(3000, alert.destroy)
        alert.bind("<Button-1>", lambda e: alert.destroy())
    
    def _on_add_patient(self) -> None:
        if not self.winfo_exists(): return
        
        # FIX: Use winfo_toplevel() as master
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Add New Patient")
        dialog.geometry("400x480")
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.resizable(False, False)
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        dialog.update_idletasks()
        try:
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 240
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
        ctk.CTkLabel(dialog, text="Add New Patient", font=ctk.CTkFont(size=18, weight="bold"), text_color=COLORS["accent"]).pack(pady=20)
        form = ctk.CTkFrame(dialog, fg_color="transparent")
        form.pack(fill="x", padx=30)
        
        ctk.CTkLabel(form, text="Patient Name:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        name_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. John Smith")
        name_entry.pack(fill="x")
        
        ctk.CTkLabel(form, text="Age:", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        age_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. 45")
        age_entry.pack(fill="x")
        
        ctk.CTkLabel(form, text="Priority (1=Critical, 10=Stable):", font=ctk.CTkFont(size=12)).pack(anchor="w", pady=(10, 2))
        prio_entry = ctk.CTkEntry(form, height=35, corner_radius=8, placeholder_text="e.g. 3")
        prio_entry.pack(fill="x")
        
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
                
                name_backend = name_input.replace(" ", "_")
                cond_backend = cond_input.replace(" ", "_")
                self.bridge.send_command(f"ADD {prio} {age} {name_backend} {cond_backend}")
                
                new_patient = PatientViewModel(0, name_input, age, prio, cond_input)
                self.patients.append(new_patient)
                self._refresh_sidebar()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Age and Priority must be numbers")
        
        ctk.CTkButton(dialog, text="Add Patient", font=ctk.CTkFont(size=14, weight="bold"), height=40, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], text_color="#1a1a2e", command=submit).pack(pady=25)
    
    def _on_treated(self) -> None:
        if not self.winfo_exists() or not self.running: return
        
        # FIX: Use winfo_toplevel()
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Doctor's Notes")
        dialog.geometry("450x200")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        try:
            dialog.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 225
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 100
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
        ctk.CTkLabel(dialog, text="📋 Enter Final Diagnosis/Treatment:", font=ctk.CTkFont(size=16, weight="bold"), text_color=COLORS["accent"]).pack(pady=(25, 15))
        diagnosis_entry = ctk.CTkEntry(dialog, width=350, height=40, font=ctk.CTkFont(size=14), placeholder_text="e.g., Treated for dehydration, discharged")
        diagnosis_entry.pack(pady=10)
        diagnosis_entry.focus()
        
        def submit():
            diagnosis = diagnosis_entry.get().strip()
            if not diagnosis: return
            dialog.destroy()
            self.current_diagnosis = diagnosis
            self.pending_extract = True
            self.bridge.send_command("EXTRACT")
        
        ctk.CTkButton(dialog, text="Discharge Patient", font=ctk.CTkFont(size=14, weight="bold"), height=40, width=200, corner_radius=10, fg_color=COLORS["success"], hover_color="#27ae60", command=submit).pack(pady=15)
        dialog.bind("<Return>", lambda e: submit())
    
    def _on_update(self) -> None:
        if not self.selected_patient:
            messagebox.showwarning("No Selection", "Select a patient first.")
            return
        if not self.winfo_exists(): return
        
        # FIX: Use winfo_toplevel()
        dialog = ctk.CTkToplevel(self.winfo_toplevel())
        dialog.title("Update Priority")
        dialog.geometry("400x280")
        dialog.resizable(False, False)
        dialog.configure(fg_color=COLORS["bg_card"])
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        
        try:
            dialog.update_idletasks()
            x = self.winfo_rootx() + (self.winfo_width() // 2) - 200
            y = self.winfo_rooty() + (self.winfo_height() // 2) - 140
            dialog.geometry(f"+{x}+{y}")
        except:
            pass
        
        ctk.CTkLabel(dialog, text=f"🔄 Update Priority", font=ctk.CTkFont(size=20, weight="bold"), text_color=COLORS["accent"]).pack(pady=(25, 10))
        ctk.CTkLabel(dialog, text=f"Patient: {self.selected_patient.name}", font=ctk.CTkFont(size=14), text_color=COLORS["text"]).pack(pady=5)
        ctk.CTkLabel(dialog, text=f"Current Priority: {self.selected_patient.priority}", font=ctk.CTkFont(size=12), text_color=COLORS["text_muted"]).pack(pady=(0, 15))
        
        entry_frame = ctk.CTkFrame(dialog, fg_color="transparent")
        entry_frame.pack(pady=10)
        ctk.CTkLabel(entry_frame, text="New Priority (1=Critical, 10=Stable):", font=ctk.CTkFont(size=12), text_color=COLORS["text"]).pack()
        prio_entry = ctk.CTkEntry(entry_frame, width=150, height=40, font=ctk.CTkFont(size=16), justify="center", placeholder_text="1-10")
        prio_entry.pack(pady=10)
        prio_entry.focus()
        
        def submit():
            try:
                new_prio = int(prio_entry.get().strip())
                if not (1 <= new_prio <= 10):
                    messagebox.showerror("Error", "Priority must be 1-10", parent=dialog)
                    return
                self.bridge.send_command(f"UPDATE {self.selected_patient.id} {new_prio}")
                self.selected_patient.priority = new_prio
                self._refresh_sidebar()
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Error", "Please enter a valid number", parent=dialog)
        
        ctk.CTkButton(dialog, text="Update Priority", font=ctk.CTkFont(size=14, weight="bold"), height=40, width=200, corner_radius=10, fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], command=submit).pack(pady=15)
        dialog.bind("<Return>", lambda e: submit())
    
    def _on_leave(self) -> None:
        if not self.selected_patient:
            messagebox.showwarning("No Selection", "Select a patient first.")
            return
        if messagebox.askyesno("Confirm", f"Remove {self.selected_patient.name}?"):
            self.bridge.send_command(f"LEAVE {self.selected_patient.id}")
    
    def _on_mass_casualty(self) -> None:
        filename = filedialog.askopenfilename(title="Select Patient Data File", filetypes=[("Text files", "*.txt"), ("All files", "*.*")], parent=self)
        if filename:
            self.bridge.send_command(f"MERGE {filename}")
    
    def _on_refresh(self) -> None:
        self.bridge.send_command("STATS")
    
    def cleanup(self) -> None:
        """Clean up resources when closing."""
        self.running = False
        try:
            self.sound_engine.stop_all()
        except Exception:
            pass
        time.sleep(0.1) # Allow threads to exit
        if not self.is_logging_out:
            try:
                self.bridge.close()
            except Exception:
                pass