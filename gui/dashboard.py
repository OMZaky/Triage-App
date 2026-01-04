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
import queue
from collections import deque
from typing import Optional, List, Callable, Deque

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
# PATIENT CARD (Reusable Widget for Sidebar)
# =============================================================================
class PatientCard(ctk.CTkFrame):
    """Reusable patient row widget to prevent destroy/create cycles."""
    
    def __init__(self, master):
        super().__init__(master, fg_color=COLORS["bg_dark"], corner_radius=10, border_width=2)
        
        self._content = ctk.CTkFrame(self, fg_color="transparent")
        self._content.pack(fill="x", padx=10, pady=8)
        
        self._name_label = ctk.CTkLabel(
            self._content, 
            text="", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=COLORS["text"]
        )
        self._name_label.pack(anchor="w")
        
        self._details_label = ctk.CTkLabel(
            self._content, 
            text="", 
            font=ctk.CTkFont(size=10), 
            text_color=COLORS["text_muted"]
        )
        self._details_label.pack(anchor="w")
        
        self._badge = ctk.CTkLabel(
            self, 
            text="", 
            font=ctk.CTkFont(size=11, weight="bold"), 
            corner_radius=5, 
            width=40, 
            height=24
        )
        self._badge.place(relx=1.0, rely=0.5, anchor="e", x=-10)
        
        self.patient_id = None  # Track who I am displaying
        self._click_callback = None
        
        # Click events
        for w in [self, self._content, self._name_label, self._details_label]:
            w.bind("<Button-1>", self._on_click)
            w.configure(cursor="hand2")
    
    def bind_click(self, callback):
        self._click_callback = callback
    
    def _on_click(self, event):
        if self._click_callback and self.patient_id is not None:
            self._click_callback(self.patient_id)
    
    def update_data(self, patient):
        """Update labels without destroying widget."""
        self.patient_id = patient.id
        color = get_priority_color(patient.priority)
        
        self.configure(border_color=color)
        self._name_label.configure(text=patient.name)
        self._details_label.configure(text=f"ID: {patient.id} | Age: {patient.age} | {patient.condition}")
        
        self._badge.configure(
            text=f"P{patient.priority}",
            fg_color=color,
            text_color=COLORS["bg_dark"] if patient.priority > 2 else COLORS["text"]
        )


# =============================================================================
# PATIENT VIEW MODEL (High-Performance Lookup Table EKG)
# =============================================================================
class PatientViewModel:
    """
    Platinum Standard Patient Model (ECGSYN-Lite).
    Features: 
    - Decoupled Visuals: Written BPM is medically accurate (Fast), 
      but Monitor Animation is cinematic (Slow/Readable).
    - Threshold Crossing Beat Detection (Perfect Audio Sync)
    """
    __slots__ = [
        'id', 'name', 'age', 'priority', 'condition',
        'heart_rate', 'spo2', 'bp_sys', 'bp_dia',
        '_base_hr', '_base_spo2', '_base_bp_sys', '_base_bp_dia',
        '_hr_drift', '_spo2_drift', '_bp_sys_drift', '_bp_dia_drift',
        'ekg_data', '_play_head', '_last_play_head', '_frame_count',
        '_resp_phase', '_resp_rate', 'beat_event'
    ]
    
    _WAVE_TEMPLATE: List[float] = []
    
    @classmethod
    def _init_template(cls) -> None:
        if cls._WAVE_TEMPLATE: return
        
        # Waveform Parameters (Lead II Standard)
        # Positive values = UP spikes
        waves = {
            'P': {'amp': 15, 'pos': 0.12, 'width': 0.025},    # P-wave UP
            'Q': {'amp': -12, 'pos': 0.20, 'width': 0.008},   # Q-dip DOWN
            'R': {'amp': 120, 'pos': 0.23, 'width': 0.012},   # R-spike BIG UP
            'S': {'amp': -25, 'pos': 0.27, 'width': 0.010},   # S-dip DOWN
            'T': {'amp': 35, 'pos': 0.42, 'width': 0.045},    # T-wave UP
            'U': {'amp': 8, 'pos': 0.55, 'width': 0.040},     # U-wave UP
        }
        
        def gaussian(x, amp, mu, sigma):
            return amp * math.exp(-((x - mu) ** 2) / (2 * sigma ** 2))
            
        for i in range(100):
            phase = i / 100.0
            y = 100.0
            if 0.05 < phase < 0.7:
                for params in waves.values():
                    y += gaussian(phase, params['amp'], params['pos'], params['width'])
            cls._WAVE_TEMPLATE.append(y)

    @staticmethod
    def _lerp(start: float, end: float, t: float) -> float:
        return start * (1.0 - t) + end * t
    
    def __init__(self, pid: int, name: str, age: int, priority: int, condition: str):
        PatientViewModel._init_template()
        self.id = pid
        self.name = name
        self.age = age
        self.priority = int(priority)
        self.condition = condition
        
        # Initial Vitals
        self._base_hr = self._calc_base_hr()
        self._base_spo2 = self._calc_base_spo2()
        self._base_bp_sys = self._calc_base_bp_sys()
        self._base_bp_dia = self._calc_base_bp_dia()
        
        self.heart_rate = self._base_hr
        self.spo2 = self._base_spo2
        self.bp_sys = self._base_bp_sys
        self.bp_dia = self._base_bp_dia
        
        self._hr_drift = 0.0
        self._spo2_drift = 0.0
        self._bp_sys_drift = 0.0
        self._bp_dia_drift = 0.0
        
        self.ekg_data = deque([100.0] * 200, maxlen=200)
        self._play_head = float(random.randint(0, 99))
        self._last_play_head = self._play_head
        self._frame_count = 0
        
        self._resp_phase = random.uniform(0, 2 * math.pi)
        self._resp_rate = random.uniform(0.02, 0.04) 
        
        self.beat_event = False
    
    def _calc_base_hr(self) -> int:
        # WRITTEN BPM: High/Realistic values
        # The text will show these high numbers (e.g., 135)
        if self.priority == 1: return 135  # Critical
        elif self.priority <= 3: return 110 # High
        elif self.priority <= 6: return 85  # Moderate
        else: return 72                    # Stable
    
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
        self._frame_count += 1
        self._resp_phase += self._resp_rate
        
        if self._frame_count >= 30:
            self._frame_count = 0
            self._update_vitals_drift()
        
        self._generate_ekg_point()

    def _update_vitals_drift(self) -> None:
        drift = 0.3 if self.priority == 1 else 0.15
        
        self._hr_drift += random.gauss(0, drift * 2)
        self._spo2_drift += random.gauss(0, drift * 0.3)
        self._bp_sys_drift += random.gauss(0, drift)
        self._bp_dia_drift += random.gauss(0, drift * 0.5)
        
        damping = 0.9
        self._hr_drift *= damping
        self._spo2_drift *= damping
        self._bp_sys_drift *= damping
        self._bp_dia_drift *= damping
        
        rsa_factor = 5.0 * math.sin(self._resp_phase)
        
        # This updates the WRITTEN heart rate (High)
        self.heart_rate = int(self._base_hr + self._hr_drift + rsa_factor)
        self.spo2 = int(max(85, min(100, self._base_spo2 + self._spo2_drift)))
        self.bp_sys = int(self._base_bp_sys + self._bp_sys_drift)
        self.bp_dia = int(self._base_bp_dia + self._bp_dia_drift)

    def _generate_ekg_point(self) -> None:
        # DECOUPLING LOGIC:
        # We want the monitor/sound to be slower (calmer) than the written text.
        # We create a "Visual BPM" that is ~60% of the real medical BPM.
        visual_bpm = self.heart_rate * 0.45
        
        # Clamp it to ensure animation never goes crazy fast or dead stop
        # Range: 45 (Slow/Resting) to 85 (Fast but readable)
        visual_bpm = max(25, min(85, visual_bpm))
        
        # Use visual_bpm for the step calculation
        step = (100 * (visual_bpm / 60.0)) / 30.0
        
        self._last_play_head = self._play_head
        self._play_head = (self._play_head + step) % 100
        
        # Lerp
        idx_floor = int(self._play_head)
        idx_ceil = (idx_floor + 1) % 100
        fraction = self._play_head - idx_floor
        
        val_start = self._WAVE_TEMPLATE[idx_floor]
        val_end = self._WAVE_TEMPLATE[idx_ceil]
        
        y = self._lerp(val_start, val_end, fraction)
        
        # Baseline Wander
        baseline_wander = 3.0 * math.sin(self._resp_phase)
        y += baseline_wander
        
        # Noise
        noise = 1.0 if self.priority == 1 else 0.4
        y += random.gauss(0, noise)
        
        # Sync Logic (Uses Visual BPM)
        peak_idx = 23
        crossed = False
        
        if self._last_play_head < peak_idx <= self._play_head:
            crossed = True
        elif self._play_head < self._last_play_head:
            # Wrap-around case: playhead crossed from ~99 back to ~0
            # Check if peak_idx was passed either before wrap or after
            if self._last_play_head < peak_idx or self._play_head >= peak_idx:
                crossed = True
                 
        if crossed and self.priority != 1:
            self.beat_event = True
                
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
        
        self.patients: dict[int, PatientViewModel] = {}  # Dict for O(1) lookups
        self.selected_patient: Optional[PatientViewModel] = None
        self.patient_count = 0
        self.estimated_wait = 0
        self.pending_extract = False
        
        self.sound_engine = SoundEngine()
        self._alarm_playing = False
        self._ekg_x_coords: List[float] = []  # Pre-calculated X coordinates
        self._card_pool: List[PatientCard] = []  # Reusable card widgets
        self.msg_queue: queue.Queue = queue.Queue()  # Thread-safe message queue
        
        self.pack(fill="both", expand=True)
        
        self._create_header()
        self._create_main_layout()
        
        self._start_status_monitor()
        self._start_animation_loop()
        self._start_cpp_listener()
        self._start_simulation_loop()
        self._process_queue_batch()  # Start the batch consumer loop
        
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
        
        # Search bar for filtering patients
        search_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        search_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *args: self._request_sidebar_refresh())
        
        self.search_entry = ctk.CTkEntry(
            search_frame,
            height=32,
            corner_radius=8,
            placeholder_text="🔍 Search by name or ID...",
            textvariable=self._search_var,
            fg_color=COLORS["bg_input"],
            border_color=COLORS["accent"]
        )
        self.search_entry.pack(fill="x")
        
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
                    self.after(33, animate)
            except Exception:
                pass
        animate()
    
    def _start_cpp_listener(self) -> None:
        """Background thread that dumps C++ messages into a thread-safe queue."""
        def listen():
            while self.running:
                try:
                    line = self.bridge.read_line()
                    if line:
                        # OPTIMIZATION: Push to queue instead of scheduling callback
                        # This prevents event loop flooding during mass data dumps
                        self.msg_queue.put(line)
                    elif line is None:
                        if not self.running: break
                        time.sleep(0.1)
                except Exception:
                    break
        threading.Thread(target=listen, daemon=True).start()
    
    def _process_queue_batch(self) -> None:
        """
        Consumes messages from the queue in batches.
        Prevents GUI freeze by processing up to 100 items per frame.
        """
        if not self.running or not self.winfo_exists():
            return
        
        # Process up to 100 messages at once (Batching)
        count = 0
        while not self.msg_queue.empty() and count < 100:
            try:
                line = self.msg_queue.get_nowait()
                self._process_response(line)
                count += 1
            except queue.Empty:
                break
        
        # Schedule next batch check in 20ms (approx 50 FPS)
        self.after(20, self._process_queue_batch)
    
    def _start_simulation_loop(self) -> None:
        def simulate():
            while self.running:
                try:
                    wait_time = random.randint(15, 45)
                    for _ in range(wait_time * 2):
                        if not self.running: return
                        time.sleep(0.5)
                    
                    if not self.running: return
                    
                    stable_patients = [p for p in self.patients.values() if p.priority > 1]
                    if stable_patients:
                        patient = random.choice(stable_patients)
                        patient.priority = 1
                        
                        self.after(0, lambda pid=patient.id: self.bridge.send_command(f"UPDATE {pid} 1"))
                        self.after(0, lambda name=patient.name: self._show_deterioration_alert(name))
                        self.after(100, self._request_sidebar_refresh)
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
            display_name = name.replace("_", " ")
            # Let backend be source of truth - refresh list from C++
            self.bridge.send_command("LIST")
            self.bridge.send_command("STATS")
            messagebox.showinfo("Patient Added", f"{display_name} added successfully!")
        
        elif cmd == "DATA":
            if len(parts) >= 6:
                pid, prio, age = int(parts[1]), int(parts[2]), int(parts[3])
                name, desc = parts[4], parts[5]
                
                # Standardize display format (remove underscores)
                display_name = name.replace("_", " ")
                display_desc = desc.replace("_", " ")
                
                if self.pending_extract:
                    self.pending_extract = False
                    # Remove patient by ID (O(1) operation)
                    if pid in self.patients:
                        del self.patients[pid]
                    
                    if self.selected_patient and self.selected_patient.id == pid:
                        self.selected_patient = None
                    
                    self._request_sidebar_refresh()
                    self._update_monitor()
                    self.bridge.send_command("STATS")
                    self.bridge.send_command("LIST")
                    
                    diagnosis = getattr(self, 'current_diagnosis', '')
                    self._show_treatment_alert(display_name, pid, prio, diagnosis)
                    self.current_diagnosis = None
                else:
                    # O(1) duplicate check with dict
                    if pid not in self.patients:
                        # FIX: Use 'display_name' and 'display_desc' instead of raw 'name'/'desc'
                        patient = PatientViewModel(pid, display_name, age, prio, display_desc)
                        self.patients[pid] = patient
                        self._request_sidebar_refresh()
                    else:
                        patient = self.patients[pid]
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
                
                # O(1) duplicate check with dict
                if pid not in self.patients:
                    patient = PatientViewModel(pid, display_name, age, prio, display_desc)
                    self.patients[pid] = patient
                    self._request_sidebar_refresh()
        
        elif cmd == "SUCCESS_UPDATE":
            messagebox.showinfo("Updated", "Patient priority updated.")
            self.bridge.send_command("STATS")
        
        elif cmd == "SUCCESS_REMOVE":
            pid = int(parts[1]) if len(parts) > 1 else 0
            # O(1) deletion with dict
            if pid in self.patients:
                del self.patients[pid]
            if self.selected_patient and self.selected_patient.id == pid:
                self.selected_patient = None
            self._request_sidebar_refresh()
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
    
    def _request_sidebar_refresh(self) -> None:
        """Request a debounced sidebar refresh - batches multiple calls into one."""
        if getattr(self, "_refresh_pending", False):
            return  # Already scheduled
        self._refresh_pending = True
        # Wait 50ms to gather all incoming data, then refresh ONCE
        self.after(50, self._execute_sidebar_refresh)
    
    def _execute_sidebar_refresh(self) -> None:
        """Execute the actual sidebar refresh."""
        self._refresh_sidebar()
        self._refresh_pending = False
    
    def _refresh_sidebar(self) -> None:
        if not self.winfo_exists(): return
        
        # 1. Get all patients
        all_patients = list(self.patients.values())
        total_count = len(all_patients)
        
        # 2. Filter by search text
        search_text = getattr(self, '_search_var', None)
        if search_text:
            query = search_text.get().strip().lower()
            if query:
                all_patients = [
                    p for p in all_patients
                    if query in p.name.lower() or query in str(p.id)
                ]
        
        filtered_count = len(all_patients)
        
        # 3. Sort by priority
        sorted_patients = sorted(all_patients, key=lambda p: p.priority)
        
        # 4. Update count label
        if filtered_count == 0 and total_count > 0:
            display_text = f"{total_count} patients (no matches)"
        elif filtered_count > 50:
            display_text = f"{filtered_count} patients (showing top 50)"
        else:
            display_text = f"{filtered_count} patients"
        self.queue_count.configure(text=display_text)
        
        # --- FIX: Only destroy labels (placeholders), preserve PatientCards ---
        for widget in self.queue_scroll.winfo_children():
            if isinstance(widget, ctk.CTkLabel):
                widget.destroy()
        
        if not sorted_patients:
            # Hide all cards (don't destroy them!)
            for card in self._card_pool:
                card.pack_forget()
                
            self.placeholder = ctk.CTkLabel(
                self.queue_scroll,
                text="No patients in queue\n\nAdd patients using\nthe control panel" if total_count == 0 else "No matches found\n\nTry a different search",
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_muted"],
                justify="center"
            )
            self.placeholder.pack(expand=True, pady=50)
            return
        # ---------------------------------------------------------------------

        # 5. RECYCLE WIDGETS
        required_count = min(len(sorted_patients), 50)
        
        while len(self._card_pool) < required_count:
            new_card = PatientCard(self.queue_scroll)
            new_card.bind_click(self._on_card_click)
            self._card_pool.append(new_card)
        
        for i in range(required_count):
            card = self._card_pool[i]
            card.update_data(sorted_patients[i])
            card.pack(fill="x", pady=4, padx=5)
        
        for i in range(required_count, len(self._card_pool)):
            self._card_pool[i].pack_forget()
    
    def _on_card_click(self, pid: int) -> None:
        """Handle click on a patient card."""
        if pid in self.patients:
            self.selected_patient = self.patients[pid]
            self._update_monitor()
    
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
        
        # Smart UI updates - only configure if value changed
        new_name = f"ID:{p.id} - {p.name}"
        if self.patient_name.cget("text") != new_name:
            self.patient_name.configure(text=new_name)
        
        new_hr = str(p.heart_rate)
        if self.hr_value.cget("text") != new_hr:
            self.hr_value.configure(text=new_hr)
        
        new_spo2 = str(p.spo2)
        if self.spo2_value.cget("text") != new_spo2:
            self.spo2_value.configure(text=new_spo2)
        
        new_bp = f"{p.bp_sys}/{p.bp_dia}"
        if self.bp_value.cget("text") != new_bp:
            self.bp_value.configure(text=new_bp)
        
        prio_color = get_priority_color(p.priority)
        new_prio = str(p.priority)
        if self.prio_value.cget("text") != new_prio:
            self.prio_value.configure(text=new_prio, text_color=prio_color)
        
        new_condition = f"Condition: {p.condition}"
        if self.condition_label.cget("text") != new_condition:
            self.condition_label.configure(text=new_condition)
        
        new_age = f"Age: {p.age} years"
        if self.age_label.cget("text") != new_age:
            self.age_label.configure(text=new_age)
        
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
        """Draw EKG using canvas recycling and pre-calculated coordinates."""
        height = self.ekg_canvas.winfo_height()
        if height < 10 or not self._ekg_x_coords: return
        
        color = get_priority_color(patient.priority)
        points = []
        
        # MATH OPTIMIZATION & RESCALING
        # Previous scale (0.005) clips the new big spikes (Amp 120).
        # Adjusted to 0.004 to fit the larger waveform comfortably.
        y_scale = height * 0.004  
        
        for i, value in enumerate(patient.ekg_data):
            if i < len(self._ekg_x_coords):
                x = self._ekg_x_coords[i]
                # Positive values go UP (Tkinter Y=0 is top)
                y = height - (value * y_scale)
                points.extend([x, y])
        
        if len(points) >= 4:
            if not self.ekg_canvas.find_withtag("ekg_line"):
                self.ekg_canvas.create_line(points, fill=color, width=2, smooth=True, tags="ekg_line")
            else:
                self.ekg_canvas.coords("ekg_line", *points)
                self.ekg_canvas.itemconfig("ekg_line", fill=color)
    
    def _on_ekg_resize(self, event=None) -> None:
        self.ekg_canvas.delete("grid")
        width = self.ekg_canvas.winfo_width()
        height = self.ekg_canvas.winfo_height()
        if width < 10 or height < 10: return
        
        # Pre-calculate X coordinates (eliminates 200 divisions per frame)
        self._ekg_x_coords = [(i / 200) * width for i in range(200)]
        
        for i in range(0, width, 20):
            self.ekg_canvas.create_line(i, 0, i, height, fill=COLORS["grid"], tags="grid")
        for i in range(0, height, 20):
            self.ekg_canvas.create_line(0, i, width, i, fill=COLORS["grid"], tags="grid")
    
    def _reset_ekg(self) -> None:
        """Hide EKG line by moving it off-screen (faster than deleting)."""
        if self.ekg_canvas.find_withtag("ekg_line"):
            self.ekg_canvas.coords("ekg_line", -10, -10, -10, -10)
    
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
                # Send to C++ backend - DO NOT create local patient
                # Wait for SUCCESS_ADD response which will refresh the list
                self.bridge.send_command(f"ADD {prio} {age} {name_backend} {cond_backend}")
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
        self.bridge.send_command("LIST")
    
    def cleanup(self) -> None:
        """Clean up resources when closing."""
        self.running = False
        try:
            self.sound_engine.stop_all()
            self.sound_engine.cleanup()  # Release pygame mixer resources
        except Exception:
            pass
        time.sleep(0.1)  # Allow threads to exit
        if not self.is_logging_out:
            try:
                self.bridge.close()
            except Exception:
                pass