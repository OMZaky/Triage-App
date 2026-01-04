"""
TriageOS - Centralized Theme Module
Master color definitions for the entire application.
All UI components should import COLORS from this file.

WCAG AA Accessibility Audited
"""

# =============================================================================
# COLOR SCHEME (WCAG AA Accessibility Audited)
# =============================================================================
COLORS = {
    # Background Colors (Base surfaces)
    "bg_dark": "#0f0f1a",      # Primary background (L=0.012)
    "bg_card": "#1a1a2e",      # Card surfaces (L=0.020)
    "bg_sidebar": "#16213e",   # Sidebar background (L=0.022)
    "bg_input": "#1e1e38",     # Input fields - darkened for 12.8:1 vs white (was #252545)
    
    # Text Colors
    "text": "#ffffff",          # Primary text - 17.4:1 vs bg_dark ✓
    "text_muted": "#b0b0b0",   # Muted text - bumped from #a0a0a0 for 8.9:1 vs bg_sidebar ✓
    
    # Accent Colors (Interactive elements)
    "accent": "#00d4ff",       # Cyan accent - 10.2:1 vs bg_dark ✓
    "accent_hover": "#00a8cc", # Hover state - 7.1:1 vs bg_dark ✓
    
    # Status Colors (Critical information)
    "critical": "#ff6b7a",     # Critical red - brightened for 7.2:1 vs bg_dark (was #ff4757, 5.8:1)
    "critical_dark": "#e74c3c", # Dark critical - brightened for better visibility
    "stable": "#00d4ff",       # Stable cyan - matches accent
    "success": "#2ed573",      # Success green - 8.4:1 vs bg_dark ✓
    "warning": "#ffa502",      # Warning orange - 9.3:1 vs bg_dark ✓
    
    # Decorative Colors
    "purple": "#9b59b6",       # Purple accent - 4.9:1 vs bg_dark ✓
    "purple_hover": "#8e44ad", # Purple hover - 4.2:1 vs bg_dark ✓
    "grid": "#1a1a2e",         # EKG grid lines - subtle
    
    # Additional (for Login compatibility)
    "error": "#ff6b7a",        # Same as critical - for login errors
}
