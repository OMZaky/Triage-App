"""
TriageOS - Backend Bridge Module
Manages the subprocess connection to the C++ triage backend (triage.exe).
Handles launching, communication, and crash recovery.

This module is GUI-agnostic - it only handles subprocess communication.

Commands Protocol:
    PUBLIC:
        LOGIN <username> <password>     -> SUCCESS_LOGIN | ERROR_LOGIN
        CHANGE_PASS <user> <old> <new>  -> SUCCESS_PASS_CHANGE | ERROR_PASS_CHANGE
        EXIT                            -> SUCCESS_EXIT
        PING                            -> PONG
    
    AUTHENTICATED:
        ADD <priority> <age> <name> <desc>  -> SUCCESS_ADD <name> ID:<id>
        EXTRACT                              -> DATA <id> <prio> <age> <name> <desc> | EMPTY
        PEEK                                 -> DATA <id> <prio> <age> <name> <desc> | EMPTY
        STATS                                -> STATS COUNT:<n> WAIT:<mins>
        UPDATE <id> <new_priority>           -> SUCCESS_UPDATE
        LEAVE <id>                           -> SUCCESS_REMOVE <id>
        MERGE <filename>                     -> SUCCESS_MERGE | ERROR_FILE_NOT_FOUND
"""

import subprocess
import threading
import sys
import os
from typing import Optional


class SystemBridge:
    """
    Manages the subprocess connection to the C++ triage backend.
    Handles launching, communication, and crash recovery.
    
    Usage:
        bridge = SystemBridge("path/to/triage.exe")
        if bridge.start():
            bridge.send_command("LOGIN admin admin")
            response = bridge.read_line()
        bridge.close()
    """
    
    def __init__(self, exe_path: str):
        """
        Initialize the bridge with the path to the C++ executable.
        
        Args:
            exe_path: Path to the triage.exe executable
        """
        self.exe_path = exe_path
        self.process: Optional[subprocess.Popen] = None
        self.is_running = False
        self.lock = threading.Lock()
    
    def start(self) -> bool:
        """
        Launches the C++ backend as a subprocess.
        
        Returns:
            True if successfully started, False otherwise
        """
        try:
            if not os.path.exists(self.exe_path):
                print(f"[Bridge] ERROR: Executable not found at '{self.exe_path}'")
                return False
            
            # Platform-specific flags to hide console window on Windows
            creation_flags = 0
            if sys.platform == "win32":
                creation_flags = subprocess.CREATE_NO_WINDOW
            
            self.process = subprocess.Popen(
                [self.exe_path],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,  # Line buffered
                creationflags=creation_flags
            )
            
            self.is_running = True
            print(f"[Bridge] C++ backend started (PID: {self.process.pid})")
            return True
            
        except FileNotFoundError:
            print(f"[Bridge] ERROR: Executable not found at '{self.exe_path}'")
            return False
        except PermissionError:
            print(f"[Bridge] ERROR: Permission denied for '{self.exe_path}'")
            return False
        except Exception as e:
            print(f"[Bridge] ERROR: Failed to start backend: {e}")
            return False
    
    def send_command(self, cmd: str) -> bool:
        """
        Sends a text command to the C++ backend via stdin.
        
        Args:
            cmd: Command string to send (e.g., "LOGIN admin admin")
            
        Returns:
            True if command was sent successfully, False otherwise
        """
        with self.lock:
            if not self.is_running or self.process is None:
                print("[Bridge] WARNING: Cannot send - backend not running")
                return False
            
            try:
                # Check if process has terminated
                if self.process.poll() is not None:
                    self.is_running = False
                    print("[Bridge] WARNING: Backend process has terminated")
                    return False
                
                self.process.stdin.write(cmd + "\n")
                self.process.stdin.flush()
                print(f"[Bridge] SENT: {cmd}")
                return True
                
            except BrokenPipeError:
                self.is_running = False
                print("[Bridge] ERROR: Broken pipe - backend crashed")
                return False
            except Exception as e:
                print(f"[Bridge] ERROR: Failed to send command: {e}")
                return False
    
    def read_line(self) -> Optional[str]:
        """
        Reads a single line from the C++ backend's stdout.
        This is a blocking call - it will wait until a line is available.
        
        Returns:
            The line read (stripped of whitespace), or None if read failed
        """
        if not self.is_running or self.process is None:
            return None
        
        try:
            line = self.process.stdout.readline()
            
            # Empty string means EOF (process terminated)
            if line == "":
                self.is_running = False
                return None
            
            result = line.strip()
            if result:
                print(f"[Bridge] RECV: {result}")
            return result
            
        except Exception as e:
            print(f"[Bridge] ERROR: Failed to read line: {e}")
            return None
    
    def check_alive(self) -> bool:
        """
        Checks if the C++ backend is still running.
        
        Returns:
            True if the process is running, False otherwise
        """
        if self.process is None:
            return False
        
        poll_result = self.process.poll()
        self.is_running = (poll_result is None)
        return self.is_running
    
    def close(self) -> None:
        """
        Gracefully shuts down the C++ backend.
        First tries EXIT command, then terminate, then kill.
        """
        with self.lock:
            if self.process is not None:
                # Try graceful shutdown via EXIT command
                try:
                    if self.is_running:
                        self.process.stdin.write("EXIT\n")
                        self.process.stdin.flush()
                        self.process.wait(timeout=2)
                except Exception:
                    pass
                
                # Try to terminate if still running
                try:
                    if self.process.poll() is None:
                        self.process.terminate()
                        self.process.wait(timeout=1)
                except Exception:
                    # Force kill as last resort
                    try:
                        self.process.kill()
                    except Exception:
                        pass
                
                print("[Bridge] C++ backend closed")
            
            self.is_running = False
            self.process = None
    
    def __enter__(self):
        """Context manager entry - starts the bridge."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes the bridge."""
        self.close()
        return False
