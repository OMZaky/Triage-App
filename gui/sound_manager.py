"""
Sound Engine for TriageOS
Handles heartbeat and alarm audio with low-latency pygame.mixer
"""

import pygame
import os


class SoundEngine:
    """
    Manages audio playback for the ER Dashboard.
    - Heartbeat: Plays once per beat with crisp timing
    - Alarm: Loops continuously until stopped
    """
    
    def __init__(self):
        """Initialize pygame mixer with low latency settings."""
        self.heartbeat_sound = None
        self.alarm_sound = None
        self._alarm_channel = None
        self._heartbeat_channel = None
        self._initialized = False
        
        try:
            # Disable video/display to prevent conflicts with tkinter
            os.environ['SDL_VIDEODRIVER'] = 'dummy'
            os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'
            
            # Pre-init for low latency, then init mixer only (not full pygame)
            pygame.mixer.pre_init(frequency=44100, size=-16, channels=2, buffer=1024)
            pygame.mixer.init()
            self._initialized = True
        except Exception as e:
            print(f"[SoundEngine] Warning: Could not initialize mixer: {e}")
            return
        
        # Get the directory where this script is located
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sounds_dir = os.path.join(base_dir, "sounds")
        
        # Load heartbeat sound
        heartbeat_path = os.path.join(sounds_dir, "heartbeat.wav")
        try:
            self.heartbeat_sound = pygame.mixer.Sound(heartbeat_path)
            self.heartbeat_sound.set_volume(1.0)
        except Exception as e:
            print(f"[SoundEngine] Warning: Could not load heartbeat.wav: {e}")
        
        # Load alarm sound
        alarm_path = os.path.join(sounds_dir, "alarm.wav")
        try:
            self.alarm_sound = pygame.mixer.Sound(alarm_path)
            self.alarm_sound.set_volume(0.3)
        except Exception as e:
            print(f"[SoundEngine] Warning: Could not load alarm.wav: {e}")
        
        # Dedicated channels for sounds
        try:
            self._alarm_channel = pygame.mixer.Channel(0)
            self._heartbeat_channel = pygame.mixer.Channel(1)
        except Exception as e:
            print(f"[SoundEngine] Warning: Could not create channels: {e}")
    
    def play_heartbeat(self) -> None:
        """Play the heartbeat sound once, force restart if playing."""
        try:
            if self.heartbeat_sound and self._heartbeat_channel:
                self._heartbeat_channel.stop()
                self._heartbeat_channel.play(self.heartbeat_sound)
        except Exception:
            pass
    
    def play_heartbeat_if_ready(self) -> None:
        """Play heartbeat only if not already playing (prevents overlap)."""
        try:
            if self.heartbeat_sound and self._heartbeat_channel:
                if not self._heartbeat_channel.get_busy():
                    self._heartbeat_channel.play(self.heartbeat_sound)
        except Exception:
            pass
    
    def play_alarm(self) -> None:
        """Play the alarm sound on infinite loop."""
        try:
            if self.alarm_sound and self._alarm_channel:
                if not self._alarm_channel.get_busy():
                    self._alarm_channel.play(self.alarm_sound, loops=-1)
        except Exception:
            pass
    
    def stop_alarm(self) -> None:
        """Stop the alarm sound specifically."""
        try:
            if self._alarm_channel:
                self._alarm_channel.stop()
        except Exception:
            pass
    
    def stop_all(self) -> None:
        """Stop all sounds."""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.stop()
        except Exception:
            pass
    
    def cleanup(self) -> None:
        """Clean up pygame mixer resources."""
        try:
            if pygame.mixer.get_init():
                pygame.mixer.quit()
        except Exception:
            pass


# Singleton instance for easy import
_instance = None

def get_sound_engine() -> SoundEngine:
    """Get or create the singleton SoundEngine instance."""
    global _instance
    if _instance is None:
        _instance = SoundEngine()
    return _instance
