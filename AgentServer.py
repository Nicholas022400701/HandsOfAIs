import json
import os
import logging
import traceback
import subprocess
import shutil
import sys
import inspect
import secrets
import threading
import time
import queue
import re
import uuid
import base64
import urllib.parse
import platform
import shlex
import io
from typing import Dict, Any, Callable, List, IO, Optional, Tuple
from pathlib import Path
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

# Import requests for synchronous HTTP calls
try:
    import requests
except ImportError:
    logging.warning("'requests' library not found. Please install it with 'pip install requests'.")
    requests = None

# Optional coloredlogs
try:
    import coloredlogs
except ImportError:
    coloredlogs = None

# Windows automation libraries (optional, for system-level automation)
try:
    import pyautogui
    import PIL.Image
    import PIL.ImageGrab
except ImportError:
    pyautogui = None
    PIL = None
    logging.warning("Windows automation libraries not found. Install with: pip install pyautogui pillow")

try:
    import pygetwindow as gw
except ImportError:
    gw = None
    logging.warning("pygetwindow not found. Install with: pip install pygetwindow")

try:
    import pyperclip
except ImportError:
    pyperclip = None
    logging.warning("pyperclip not found. Install with: pip install pyperclip")

# Windows UI Automation (for getting screen info without screenshots)
try:
    import uiautomation as auto
except ImportError:
    auto = None
    logging.warning("uiautomation not found. Install with: pip install uiautomation")

# OCR for text extraction from screen
try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    logging.warning("pytesseract not found. Install with: pip install pytesseract")

# SSH Library Import (Keeping SSH as it might be useful, but not required for WSL)
try:
    import paramiko
except ImportError:
    paramiko = None

# Web Server Imports
try:
    from flask import Flask, request, jsonify
    from flask_cors import CORS
except ImportError:
    logging.error("Flask or Flask-CORS not found. Please install them: pip install Flask Flask-CORS")
    sys.exit(1)

# === Configuration ===
class Config:
    WORKSPACE_DIR = Path("./").resolve()
    DEFAULT_TIMEOUT = 60 # Increased timeout for potentially slower WSL interactions
    MAX_TIMEOUT = 3600
    SERVER_HOST = '127.0.0.1'
    SERVER_PORT = 5005
    ALLOWED_CORS_ORIGINS = ["https://gemini.google.com", "https://aistudio.google.com"]
    API_SECRET_KEY = "E8b2a1a2e9b1f0c1d1a9E8FF7aka55riotr0knlMMNF6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
    # Configuration for WSL. Change 'Ubuntu' if using a different distribution.
    WSL_DISTRIBUTION = "Ubuntu" 

# Initialize Logging
log = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [AGENT] - %(levelname)s - %(message)s')
if coloredlogs:
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    coloredlogs.install(level='INFO', logger=log, fmt='%(asctime)s - [AGENT] - %(levelname)s - %(message)s')

# Global ThreadPoolExecutor
executor_pool = ThreadPoolExecutor(max_workers=10)

class JobManager:
    # (JobManager implementation remains the same, omitted for brevity as it wasn't criticized)
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.lock = threading.Lock()

    def create_job(self) -> str:
        with self.lock:
            job_id = str(uuid.uuid4())
            self.jobs[job_id] = {"status": "starting", "queue": queue.Queue(), "start_time": time.time()}
            return job_id

    def get_job_update(self, job_id: str) -> Dict[str, Any]:
        # (Implementation omitted for brevity)
        return {"status": "error", "message": "Job management not fully implemented in this snippet."}


# === Session Management (Refactored for persistent subprocesses like WSL) ===

class Session:
    def __init__(self, session_type: str):
        self.id = str(uuid.uuid4())
        self.type = session_type
        self.process: Optional[subprocess.Popen] = None
        
        # SSH specific (if implemented later)
        self.ssh_client = None
        
        # Subprocess specific (WSL/Local)
        self.stdout_queue = queue.Queue()
        self.stderr_queue = queue.Queue()
        self.reader_threads: List[threading.Thread] = []
        self.lock = threading.Lock() # Ensures sequential command execution in the session

    def _stream_reader(self, pipe: IO[bytes], q: queue.Queue):
        """Reads from a pipe (in bytes) and puts the output into a queue (decoded)."""
        try:
            # Read line by line until the pipe closes
            for line in iter(pipe.readline, b''):
                # Decode assuming UTF-8, standard for WSL/Linux
                q.put(line.decode('utf-8', errors='replace'))
        except Exception as e:
            if self.is_alive(): # Only log if the session is supposed to be alive
                log.error(f"Error reading stream in session {self.id}: {e}")
        finally:
            pipe.close()

    def start_subprocess(self, command: List[str]):
        """Starts the persistent subprocess and the reader threads."""
        try:
            # Start Popen using bytes (text=False) for robust cross-platform interaction
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                bufsize=0 # Unbuffered
            )
            
            # Start reader threads
            t_stdout = threading.Thread(target=self._stream_reader, args=(self.process.stdout, self.stdout_queue), daemon=True)
            t_stderr = threading.Thread(target=self._stream_reader, args=(self.process.stderr, self.stderr_queue), daemon=True)
            t_stdout.start()
            t_stderr.start()
            self.reader_threads.extend([t_stdout, t_stderr])
            log.info(f"Started subprocess session {self.id} (PID: {self.process.pid})")

        except Exception as e:
            log.error(f"Failed to start subprocess for session {self.id}: {e}")
            raise

    def initialize_shell(self, init_commands: List[str]):
        """Sends initial commands to configure the shell (e.g., disable echo, set PS1)."""
        if not self.process or not self.process.stdin:
            raise RuntimeError("Process not running or stdin not available.")
        
        log.info(f"Initializing shell environment for session {self.id}...")
        for cmd in init_commands:
            # Encode commands to bytes before writing
            self.process.stdin.write((cmd + "\n").encode('utf-8'))
            self.process.stdin.flush()
        
        # Allow time for commands to execute and clear the initial output buffer (like MOTD)
        time.sleep(1.5)
        self._clear_queues()
        log.info(f"Shell environment initialized for session {self.id}.")

    def _clear_queues(self):
        while not self.stdout_queue.empty():
            try: self.stdout_queue.get_nowait()
            except queue.Empty: break
        while not self.stderr_queue.empty():
            try: self.stderr_queue.get_nowait()
            except queue.Empty: break

    def run_command(self, command: str, timeout: int) -> Dict[str, Any]:
        # Ensure only one command executes at a time in this session
        if not self.lock.acquire(timeout=5):
             return {"status": "error", "message": "Session is busy executing another command."}

        try:
            if not self.is_alive():
                return {"status": "error", "message": "Session is not active or has been terminated.", "returncode": -1}

            if self.type in ['wsl_shell', 'local_shell']:
                # === MODIFICATION: Point to the new, robust command executor ===
                return self._run_subprocess_command_v2(command, timeout)
            
            # (SSH implementation omitted)
            
            else:
                return {"status": "error", "message": f"Unsupported session type: {self.type}", "returncode": -1}
        finally:
            self.lock.release()

    def _run_subprocess_command_v2(self, command: str, timeout: int) -> Dict[str, Any]:
        """
        [REWRITTEN V2.1] Executes a command by reading the stdout queue line-by-line
        to deterministically find the end_marker and parse the return code,
        avoiding all race conditions.
        """
        start_marker = f"AG_START_{secrets.token_hex(8)}"
        end_marker = f"AG_END_{secrets.token_hex(8)}"
        
        # === FIX V2.1: $RETVAL must be OUTSIDE the single quotes to be expanded by the shell ===
        full_command = f"echo '{start_marker}'; {command}; RETVAL=$?; echo '{end_marker}' $RETVAL\n"
        
        stdout_lines = []
        stderr_lines = []
        
        try:
            if not self.process or not self.process.stdin:
                raise RuntimeError("Process died unexpectedly.")
                
            self._clear_queues() # Clear residual output
                
            # Write the command (encoded as bytes)
            self.process.stdin.write(full_command.encode('utf-8'))
            self.process.stdin.flush()

            start_time = time.time()
            returncode = -1
            found_start_marker = False
            
            # --- REWRITTEN LOOP ---
            while True:
                if time.time() - start_time > timeout:
                    # Note: This timeout only stops waiting. It does NOT kill the running command in the shell.
                    raise TimeoutError(f"Command timed out waiting for output after {timeout} seconds.")
                
                if not self.is_alive():
                    raise RuntimeError("Session died unexpectedly during command execution.")

                # Try to read one line from stdout queue (blocking with a short timeout)
                try:
                    line = self.stdout_queue.get(timeout=0.1) # Block for 100ms
                    
                    if end_marker in line:
                        # This is the last line. Parse the return code.
                        try:
                            # The line is "AG_END_... 0\n"
                            returncode_str = line.split()[-1]
                            returncode = int(returncode_str)
                        except (IndexError, ValueError):
                            log.warning(f"Could not parse return code from end marker line: '{line}'")
                            returncode = -1 # Parsing failed
                        
                        # We are done. Break the loop.
                        break 
                    
                    if not found_start_marker:
                        if start_marker in line:
                            found_start_marker = True
                        # Discard all output (like MOTD) until we see the start marker
                        continue
                    else:
                        # This is a regular stdout line after the start marker
                        stdout_lines.append(line)
                        
                except queue.Empty:
                    # stdout_queue was empty, just loop again (checks timeout, stderr)
                    pass 

                # Non-blocking read from stderr (drain it completely on each loop)
                try:
                    while True: stderr_lines.append(self.stderr_queue.get_nowait())
                except queue.Empty: pass
            
            # --- END REWRITTEN LOOP ---
            
            # We broke the loop. Combine the lines.
            stdout_buffer = "".join(stdout_lines)
            
            # Drain any remaining stderr output that might have arrived
            try:
                while True: stderr_lines.append(self.stderr_queue.get_nowait())
            except queue.Empty: pass
            
            stderr_buffer = "".join(stderr_lines)

            return {"status": "success" if returncode == 0 else "error", "stdout": stdout_buffer, "stderr": stderr_buffer, "returncode": returncode}

        except Exception as e:
            log.error(f"Exception in subprocess session {self.id}: {traceback.format_exc()}")
            # Return whatever we managed to capture before the error
            return {"status": "error", "message": str(e), "stdout": "".join(stdout_lines), "stderr": "".join(stderr_lines), "returncode": -1}

    def is_alive(self) -> bool:
        if self.type in ['wsl_shell', 'local_shell']:
            return self.process is not None and self.process.poll() is None
        # (SSH is_alive omitted)
        return False

    def close(self):
        log.info(f"Closing session {self.id} ({self.type})...")
        
        if self.process:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        
        for t in self.reader_threads:
            t.join(timeout=2)

class SessionManager:
    def __init__(self):
        self.sessions: Dict[str, Session] = {}
        self.lock = threading.Lock()
        # Automatically start a default execution session
        self.default_session_id: Optional[str] = None
        self._initialize_default_session()

    def _initialize_default_session(self):
        log.info("Initializing default execution environment...")
        # Prefer WSL on Windows
        if platform.system() == "Windows":
            result = self.start_session(session_type="wsl_shell")
            if result['status'] == 'success':
                self.default_session_id = result['session_id']
                log.info(f"Default environment set to WSL (Session ID: {self.default_session_id})")
            else:
                log.error("Failed to start default WSL session. Functionality will be limited. Check WSL installation.")
                log.error(f"Error details: {result.get('message')}")
        else:
            # Use local shell on Linux/macOS
            result = self.start_session(session_type="local_shell")
            if result['status'] == 'success':
                self.default_session_id = result['session_id']
                log.info(f"Default environment set to Local Shell (Session ID: {self.default_session_id})")
            else:
                 log.error("Failed to start default local shell session.")


    def start_session(self, session_type: str, details: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        session = Session(session_type)
        details = details or {}
        try:
            if session_type == 'wsl_shell':
                if platform.system() != "Windows":
                    return {"status": "error", "message": "WSL sessions are only available on Windows."}
                
                distro = details.get('distro', Config.WSL_DISTRIBUTION)
                command = ["wsl.exe", "-d", distro, "/bin/bash"]
                
                try:
                    session.start_subprocess(command)
                except FileNotFoundError:
                     return {"status": "error", "message": f"WSL executable not found or distribution '{distro}' missing."}
                
                # Initialize the shell environment for automation
                init_commands = [
                    "stty -echo",          # Disable echo
                    "export PS1=''",       # Clear the prompt
                    "export LANG=C.UTF-8",  # Ensure UTF-8 encoding
                    "unset PROMPT_COMMAND", # Prevent interference from custom prompts
                    
                    # --- 把你的代理加在这里 ---
                    # (如果端口不是 7890，请修改)
                    "export http_proxy='http://127.0.0.1:7890'",
                    "export https_proxy='http://127.0.0.1:7890'",
                    "export no_proxy='localhost,127.0.0.1'"
                ]
                session.initialize_shell(init_commands)

            elif session_type == 'local_shell':
                 # Starts a local interactive shell (Linux/macOS only)
                if platform.system() == "Windows":
                     return {"status": "error", "message": "Interactive local_shell is not supported on Windows. Use 'wsl_shell'."}
                
                command = ["/bin/bash"]
                session.start_subprocess(command)
                
                init_commands = [
                    "stty -echo", "export PS1=''", "export LANG=C.UTF-8", "unset PROMPT_COMMAND"
                ]
                session.initialize_shell(init_commands)

            # (SSH logic omitted)

            else:
                return {"status": "error", "message": f"Unsupported session type: {session_type}"}

            # Final check
            if not session.is_alive():
                raise RuntimeError("Session failed to start or died immediately.")

            with self.lock:
                self.sessions[session.id] = session
            
            # If this is the first session and default is missing, set it.
            if self.default_session_id is None:
                self.default_session_id = session.id

            return {"status": "success", "message": f"Session {session.id} ({session_type}) started.", "session_id": session.id}

        except Exception as e:
            session.close()
            log.error(f"Failed to start session {session_type}: {traceback.format_exc()}")
            return {"status": "error", "message": f"Failed to start session: {e}"}

    def run_in_session(self, session_id: Optional[str], command: str, timeout: int) -> Dict[str, Any]:
        # If session_id is None, use the default session
        target_session_id = session_id or self.default_session_id
        
        if target_session_id is None:
             return {"status": "error", "message": "No active session available (default session failed to start)."}

        with self.lock: 
            session = self.sessions.get(target_session_id)
        
        if not session: 
            # Handle case where default_session_id might point to a closed session
            if target_session_id == self.default_session_id:
                self.default_session_id = None
            return {"status": "error", "message": f"Session ID {target_session_id} not found or closed."}
        
        return session.run_command(command, timeout)

    def close_session(self, session_id: str) -> Dict[str, Any]:
        with self.lock: 
            session = self.sessions.pop(session_id, None)
        
        if not session: 
            return {"status": "error", "message": f"Session ID {session_id} not found."}
        
        if session_id == self.default_session_id:
            self.default_session_id = None

        session.close()
        return {"status": "success", "message": f"Session {session_id} closed."}

    def close_all(self):
        with self.lock: 
            for session_id in list(self.sessions.keys()):
                session = self.sessions.pop(session_id)
                session.close()
            self.default_session_id = None

class SafetySandbox:
    @staticmethod
    def sanitize_path(relative_path: str) -> Path:
        if not relative_path: return Config.WORKSPACE_DIR
        try:
            base = Config.WORKSPACE_DIR
            unsafe_path = (base / relative_path).resolve()
            # Ensure the resolved path is still within the workspace
            unsafe_path.relative_to(base)
            return unsafe_path
        except (ValueError, RuntimeError): 
            # Catches path traversal attempts
            raise PermissionError(f"Path traversal attempt or invalid path: {relative_path}")
    
    @staticmethod
    def translate_path_for_session(host_path: Path, session_type: str) -> str:
        """Converts a host Path object to the path format required by the session environment."""
        
        if session_type == 'wsl_shell':
            if platform.system() != "Windows":
                # Should not happen if session management is correct, but as a fallback:
                return host_path.as_posix()
            
            # Convert Windows path (C:\...) to WSL path (/mnt/c/...)
            try:
                drive_letter = host_path.drive[0].lower()
                # Get the path relative to the drive root and convert separators
                relative_path_posix = host_path.relative_to(host_path.anchor).as_posix()
                wsl_path = f"/mnt/{drive_letter}/{relative_path_posix}"
                return wsl_path
            except Exception as e:
                raise ValueError(f"Could not translate Windows path '{host_path}' to WSL path: {e}")
        
        elif session_type == 'local_shell':
            # Local shell uses the host path format
            return str(host_path)
        
        else:
            raise ValueError(f"Path translation not supported for session type: {session_type}")

class Toolbelt:
    def __init__(self, agent_executor):
        self.executor = agent_executor
        # Removed modify_file
        self.tools: Dict[str, Callable] = {
            "list_files": self.list_files,
            "read_file": self.read_file,
            "write_file": self.write_file,
            "append_file": self.append_file,
            "make_directory": self.make_directory,
            "delete_path": self.delete_path,
            "execute_python_script": self.execute_python_script,
            "execute_shell_command": self.execute_shell_command,
            "session_start": self.session_start,
            "session_run": self.session_run,
            "session_close": self.session_close,
            "check_update_error": self.check_update_error,
            "search_arxiv": self.search_arxiv,
            # Windows system-level automation tools
            "capture_screen": self.capture_screen,
            "simulate_keyboard": self.simulate_keyboard,
            "simulate_mouse": self.simulate_mouse,
            "get_windows": self.get_windows,
            "clipboard_operations": self.clipboard_operations,
            # Screen information without screenshots (token-efficient)
            "get_screen_info": self.get_screen_info,
            "find_ui_element": self.find_ui_element,
        }

    def _validate_timeout(self, timeout: Optional[int]) -> int:
        if timeout is None or timeout <= 0: return Config.DEFAULT_TIMEOUT
        if timeout > Config.MAX_TIMEOUT: return Config.MAX_TIMEOUT
        return timeout

    # --- Session Tools ---
    def session_start(self, session_type: str, details: Optional[Dict] = None, timeout: int = 30) -> Dict[str, Any]:
        """Starts a new interactive session (wsl_shell, local_shell)."""
        return self.executor.session_manager.start_session(session_type, details, timeout)

    def session_run(self, command: str, session_id: Optional[str] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Runs a command in an interactive session. Uses the default session if session_id is None."""
        effective_timeout = self._validate_timeout(timeout)
        # Pass session_id (which might be None) to the manager, so it uses the default.
        return self.executor.session_manager.run_in_session(session_id, command, effective_timeout)

    def session_close(self, session_id: str) -> Dict[str, Any]:
        """Closes an interactive session."""
        return self.executor.session_manager.close_session(session_id)
    
    # --- Arxiv Search (Refactored to use requests and ThreadPoolExecutor) ---
    
    def _fetch_arxiv_one(self, keyword: str, max_results: int, sort_by: str, sort_order: str, proxy: Optional[str]) -> Dict[str, Any]:
        """Synchronous helper function to fetch results for a single keyword."""
        try:
            encoded_keyword = urllib.parse.quote(keyword)
            url = f"http://export.arxiv.org/api/query?search_query=all:{encoded_keyword}&start=0&max_results={max_results}&sortBy={sort_by}&sortOrder={sort_order}"
            
            # === FIX (Logic): Use proxy if it's not None (even if it's "") ===
            # This allows passing proxy="" to *disable* proxy use.
            proxies = {"http": proxy, "https": proxy} if proxy is not None else None
            # === END FIX ===
            
            log.info(f"Fetching ArXiv URL: {url} (Proxy: {proxies})")
            response = requests.get(url, timeout=20, proxies=proxies)
            response.raise_for_status()
            
            # XML Parsing
            root = ET.fromstring(response.text)
            entries = []
            ns = {'atom': 'http://www.w3.org/2005/Atom'}

            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text
                summary = entry.find('atom:summary', ns).text
                entries.append({
                    "title": title.strip().replace('\n', ' ') if title else "",
                    "summary": summary.strip().replace('\n', ' ') if summary else "",
                    "published": entry.find('atom:published', ns).text,
                    "authors": [author.find('atom:name', ns).text for author in entry.findall('atom:author', ns)],
                    "id_url": entry.find('atom:id', ns).text
                })
            return {"keyword": keyword, "status": "success", "results": entries}
        
        except Exception as e:
            log.error(f"ArXiv request failed for keyword '{keyword}': {e}")
            return {"keyword": keyword, "status": "error", "error_message": str(e)}

    def search_arxiv(self, keywords: List[str], max_results: int = 5, sort_by: str = "relevance", sort_order: str = "descending", proxy: Optional[str] = "http://127.0.0.1:7890") -> Dict[str, Any]:
        """
        Searches Arxiv concurrently for multiple keywords using a ThreadPoolExecutor.
        [MODIFIED]: Defaults to proxy 'http://127.0.0.1:7890'.
        """
        if requests is None:
            return {"status": "error", "message": "'requests' library is not installed."}

        if sort_by not in ["relevance", "lastUpdatedDate", "submittedDate"]: sort_by = "relevance"
        if sort_order not in ["ascending", "descending"]: sort_order = "descending"
        
        # === FIX (Default): Set default proxy in signature ===
        # The 'proxy' argument now defaults to your proxy.
        # Passing proxy="" will disable it (thanks to the fix in _fetch_arxiv_one).
        # Passing a different string will override it.
        # === END FIX ===

        from functools import partial
        fetch_func = partial(self._fetch_arxiv_one, max_results=max_results, sort_by=sort_by, sort_order=sort_order, proxy=proxy)
        
        results = list(executor_pool.map(fetch_func, keywords))
        
        return {"status": "success", "message": f"Completed searches for {len(keywords)} keywords", "results": results}

    def check_update_error(self) -> Dict[str, Any]:
        """Checks if the launcher reported an error during the last update attempt."""
        error_log_path = Config.WORKSPACE_DIR / "update_error.log"
        try:
            if not error_log_path.exists():
                return {"status": "success", "error_found": False}
            
            error_details = error_log_path.read_text(encoding='utf-8')
            os.remove(error_log_path) # Delete after reading
            return {"status": "success", "error_found": True, "details": error_details}
        except Exception as e:
            return {"status": "error", "message": f"Error checking update log: {e}"}


    # --- Execution Tools (Refactored for Session usage) ---

    def execute_shell_command(self, command_line: str, timeout: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Executes a shell command using the specified or default session. This replaces direct host execution."""
        
        # This tool now simply acts as an alias for session_run using the default behavior.
        return self.session_run(command_line, session_id=session_id, timeout=timeout)

    # Refactored to run Python inside the execution environment (WSL/Session)
    def execute_python_script(self, filename: str, timeout: Optional[int] = None, session_id: Optional[str] = None) -> Dict[str, Any]:
        """Executes a Python script within the active session environment (e.g., WSL), not on the host."""
        
        # 1. Validate file path on the host
        try:
            path = SafetySandbox.sanitize_path(filename)
            if not path.is_file() or not filename.lower().endswith(".py"): 
                return {"status": "error", "message": "File not found or not a Python script."}
        except PermissionError as e:
            return {"status": "error", "message": str(e)}

        # 2. Determine the session to use
        target_session_id = session_id or self.executor.session_manager.default_session_id
        if not target_session_id:
             return {"status": "error", "message": "No active session available for script execution."}

        # We need the session object to determine the type for path translation
        session = self.executor.session_manager.sessions.get(target_session_id)
        if not session:
             return {"status": "error", "message": f"Session {target_session_id} not found."}

        # 3. Translate the path
        try:
            script_path_in_env = SafetySandbox.translate_path_for_session(path, session.type)
        except ValueError as e:
            return {"status": "error", "message": str(e)}

        # 4. Construct the command (using python3, standard in modern Linux/WSL)
        # Use shlex.quote to handle paths with spaces or special characters safely
        command = f"python3 {shlex.quote(script_path_in_env)}"
        
        log.info(f"Executing Python script in session {target_session_id} ({session.type}): {command}")
        
        # 5. Execute the command using session_run
        return self.session_run(command, session_id=target_session_id, timeout=timeout)

    # --- File System Tools (Remain the same, operating on the host workspace) ---

    def list_files(self, subdir: str = "", recursive: bool = False) -> Dict[str, Any]:
        try:
            path = SafetySandbox.sanitize_path(subdir)
            if not path.is_dir():
                 return {"status": "error", "message": "Directory not found."}

            if recursive: 
                items = [{"name": str(p.relative_to(path)), "type": "d" if p.is_dir() else "f"} for p in path.rglob('*')]
            else: 
                items = [{"name": p.name, "type": "d" if p.is_dir() else "f"} for p in path.iterdir()]
            
            return {"status": "success", "items": items}
        except Exception as e: 
            return {"status": "error", "message": f"Failed to list files: {e}"}

    def read_file(self, filename: str) -> Dict[str, Any]:
        try:
            path = SafetySandbox.sanitize_path(filename)
            if not path.is_file(): return {"status": "error", "message": "File not found."}
            return {"status": "success", "content": path.read_text(encoding='utf-8', errors='ignore')}
        except Exception as e: return {"status": "error", "message": f"Failed to read file: {e}"}

    def write_file(self, filename: str, content: str) -> Dict[str, Any]:
        try:
            path = SafetySandbox.sanitize_path(filename)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding='utf-8')
            return {"status": "success", "message": f"Wrote to {filename}"}
        except Exception as e: return {"status": "error", "message": f"Failed to write file: {e}"}

    def append_file(self, filename: str, content: str) -> Dict[str, Any]:
        try:
            path = SafetySandbox.sanitize_path(filename)
            if not path.exists():
                 return {"status": "error", "message": "File not found."}
            with open(path, 'a', encoding='utf-8') as f: f.write(content)
            return {"status": "success", "message": f"Appended to {filename}"}
        except Exception as e: return {"status": "error", "message": f"Failed to append: {e}"}

    # modify_file was removed as requested.

    def make_directory(self, dirname: str) -> Dict[str, Any]:
        try:
            SafetySandbox.sanitize_path(dirname).mkdir(parents=True, exist_ok=True)
            return {"status": "success", "message": f"Directory {dirname} created."}
        except Exception as e: return {"status": "error", "message": f"Failed to create directory: {e}"}

    def delete_path(self, path_str: str, user_confirmed: bool = False) -> Dict[str, Any]:
        try:
            path = SafetySandbox.sanitize_path(path_str)
            if not path.exists(): return {"status": "error", "message": "Path not found."}
            if not user_confirmed: 
                return {"status": "pending_confirmation", "message": f"Awaiting confirmation to delete {path_str}."}
            
            if path.is_file(): 
                path.unlink()
            elif path.is_dir(): 
                shutil.rmtree(path)
            
            return {"status": "success", "message": f"Successfully deleted {path_str}"}
        except Exception as e: return {"status": "error", "message": f"Failed to delete path: {e}"}

    # --- Windows System-Level Automation Tools ---

    def capture_screen(self, region: Optional[str] = None, filename: Optional[str] = None, 
                       window_title: Optional[str] = None, return_base64: bool = True) -> Dict[str, Any]:
        """
        Captures a screenshot of the screen or a specific window.
        
        Args:
            region: Optional region to capture as "x,y,width,height" (e.g., "100,100,800,600")
            filename: Optional filename to save the screenshot (saved in workspace)
            window_title: Optional window title to capture (partial match)
            return_base64: If True, returns the image as base64 string in the response
        
        Returns:
            Dict with status, optional base64 image data, and file path if saved
        """
        if pyautogui is None or PIL is None:
            return {"status": "error", "message": "Screen capture not available. Install with: pip install pyautogui pillow"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            screenshot = None
            
            # Capture specific window
            if window_title:
                if gw is None:
                    return {"status": "error", "message": "Window capture requires pygetwindow. Install with: pip install pygetwindow"}
                
                windows = gw.getWindowsWithTitle(window_title)
                if not windows:
                    return {"status": "error", "message": f"No window found with title containing '{window_title}'"}
                
                win = windows[0]
                if win.isMinimized:
                    return {"status": "error", "message": "Target window is minimized. Cannot capture."}
                
                # Capture window region
                screenshot = pyautogui.screenshot(region=(win.left, win.top, win.width, win.height))
            
            # Capture specific region
            elif region:
                try:
                    x, y, w, h = map(int, region.split(','))
                    screenshot = pyautogui.screenshot(region=(x, y, w, h))
                except ValueError:
                    return {"status": "error", "message": "Invalid region format. Use 'x,y,width,height'"}
            
            # Capture full screen
            else:
                screenshot = pyautogui.screenshot()
            
            result = {"status": "success"}
            
            # Save to file if requested
            if filename:
                try:
                    filepath = SafetySandbox.sanitize_path(filename)
                    filepath.parent.mkdir(parents=True, exist_ok=True)
                    screenshot.save(str(filepath))
                    result["saved_to"] = filename
                except Exception as e:
                    return {"status": "error", "message": f"Failed to save screenshot: {e}"}
            
            # Return base64 encoded image
            if return_base64:
                buffer = io.BytesIO()
                screenshot.save(buffer, format='PNG')
                img_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                result["image_base64"] = img_base64
                result["image_size"] = {"width": screenshot.width, "height": screenshot.height}
            
            result["message"] = "Screenshot captured successfully"
            return result
            
        except Exception as e:
            log.error(f"Screen capture error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Screen capture failed: {e}"}

    def simulate_keyboard(self, action: str, text: Optional[str] = None, 
                         key: Optional[str] = None, keys: Optional[List[str]] = None,
                         interval: float = 0.0) -> Dict[str, Any]:
        """
        Simulates keyboard input.
        
        Args:
            action: Action to perform - 'type', 'press', 'hotkey'
            text: Text to type (for 'type' action)
            key: Single key to press (for 'press' action)
            keys: List of keys for hotkey combination (for 'hotkey' action, e.g., ['ctrl', 'c'])
            interval: Delay between keystrokes in seconds (for 'type' action)
        
        Returns:
            Dict with status and message
        """
        if pyautogui is None:
            return {"status": "error", "message": "Keyboard simulation not available. Install with: pip install pyautogui"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            if action == 'type':
                if not text:
                    return {"status": "error", "message": "Text is required for 'type' action"}
                pyautogui.write(text, interval=interval)
                return {"status": "success", "message": f"Typed text: {text[:50]}{'...' if len(text) > 50 else ''}"}
            
            elif action == 'press':
                if not key:
                    return {"status": "error", "message": "Key is required for 'press' action"}
                pyautogui.press(key)
                return {"status": "success", "message": f"Pressed key: {key}"}
            
            elif action == 'hotkey':
                if not keys or len(keys) < 2:
                    return {"status": "error", "message": "At least 2 keys required for 'hotkey' action (e.g., ['ctrl', 'c'])"}
                pyautogui.hotkey(*keys)
                return {"status": "success", "message": f"Pressed hotkey: {'+'.join(keys)}"}
            
            else:
                return {"status": "error", "message": f"Unknown action: {action}. Use 'type', 'press', or 'hotkey'"}
        
        except Exception as e:
            log.error(f"Keyboard simulation error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Keyboard simulation failed: {e}"}

    def simulate_mouse(self, action: str, x: Optional[int] = None, y: Optional[int] = None,
                      button: str = 'left', clicks: int = 1, duration: float = 0.0) -> Dict[str, Any]:
        """
        Simulates mouse operations.
        
        Args:
            action: Action to perform - 'move', 'click', 'drag', 'scroll', 'position'
            x, y: Coordinates (for move, click, drag actions)
            button: Mouse button - 'left', 'right', 'middle' (for click action)
            clicks: Number of clicks (for click action)
            duration: Duration of movement in seconds (for move and drag actions)
        
        Returns:
            Dict with status, message, and current position
        """
        if pyautogui is None:
            return {"status": "error", "message": "Mouse simulation not available. Install with: pip install pyautogui"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            if action == 'position':
                pos = pyautogui.position()
                return {"status": "success", "position": {"x": pos.x, "y": pos.y}}
            
            elif action == 'move':
                if x is None or y is None:
                    return {"status": "error", "message": "x and y coordinates required for 'move' action"}
                pyautogui.moveTo(x, y, duration=duration)
                return {"status": "success", "message": f"Moved to ({x}, {y})", "position": {"x": x, "y": y}}
            
            elif action == 'click':
                if x is not None and y is not None:
                    pyautogui.click(x, y, clicks=clicks, button=button)
                    msg = f"Clicked {button} button {clicks} time(s) at ({x}, {y})"
                else:
                    pyautogui.click(clicks=clicks, button=button)
                    pos = pyautogui.position()
                    msg = f"Clicked {button} button {clicks} time(s) at current position ({pos.x}, {pos.y})"
                return {"status": "success", "message": msg}
            
            elif action == 'scroll':
                if x is None:
                    return {"status": "error", "message": "Scroll amount (x parameter) required for 'scroll' action"}
                pyautogui.scroll(x)
                return {"status": "success", "message": f"Scrolled {x} units"}
            
            else:
                return {"status": "error", "message": f"Unknown action: {action}. Use 'move', 'click', 'scroll', or 'position'"}
        
        except Exception as e:
            log.error(f"Mouse simulation error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Mouse simulation failed: {e}"}

    def get_windows(self, action: str = 'list', title: Optional[str] = None) -> Dict[str, Any]:
        """
        Lists or manages windows.
        
        Args:
            action: Action to perform - 'list', 'activate', 'minimize', 'maximize', 'close'
            title: Window title (partial match) for actions other than 'list'
        
        Returns:
            Dict with status and window information
        """
        if gw is None:
            return {"status": "error", "message": "Window management not available. Install with: pip install pygetwindow"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            if action == 'list':
                all_windows = gw.getAllWindows()
                # Filter out windows with empty titles
                windows_info = [
                    {"title": w.title, "left": w.left, "top": w.top, 
                     "width": w.width, "height": w.height, 
                     "minimized": w.isMinimized, "maximized": w.isMaximized,
                     "active": w.isActive}
                    for w in all_windows if w.title.strip()
                ]
                return {"status": "success", "windows": windows_info, "count": len(windows_info)}
            
            else:
                if not title:
                    return {"status": "error", "message": f"Window title required for '{action}' action"}
                
                windows = gw.getWindowsWithTitle(title)
                if not windows:
                    return {"status": "error", "message": f"No window found with title containing '{title}'"}
                
                win = windows[0]
                
                if action == 'activate':
                    if win.isMinimized:
                        win.restore()
                    win.activate()
                    return {"status": "success", "message": f"Activated window: {win.title}"}
                
                elif action == 'minimize':
                    win.minimize()
                    return {"status": "success", "message": f"Minimized window: {win.title}"}
                
                elif action == 'maximize':
                    win.maximize()
                    return {"status": "success", "message": f"Maximized window: {win.title}"}
                
                elif action == 'close':
                    win.close()
                    return {"status": "success", "message": f"Closed window: {win.title}"}
                
                else:
                    return {"status": "error", "message": f"Unknown action: {action}"}
        
        except Exception as e:
            log.error(f"Window management error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Window management failed: {e}"}

    def clipboard_operations(self, action: str, text: Optional[str] = None) -> Dict[str, Any]:
        """
        Performs clipboard operations.
        
        Args:
            action: Action to perform - 'get', 'set', 'clear'
            text: Text to set to clipboard (for 'set' action)
        
        Returns:
            Dict with status and clipboard content (for 'get' action)
        """
        if pyperclip is None:
            return {"status": "error", "message": "Clipboard operations not available. Install with: pip install pyperclip"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            if action == 'get':
                content = pyperclip.paste()
                return {"status": "success", "content": content, "length": len(content)}
            
            elif action == 'set':
                if text is None:
                    return {"status": "error", "message": "Text is required for 'set' action"}
                pyperclip.copy(text)
                return {"status": "success", "message": f"Copied {len(text)} characters to clipboard"}
            
            elif action == 'clear':
                pyperclip.copy('')
                return {"status": "success", "message": "Clipboard cleared"}
            
            else:
                return {"status": "error", "message": f"Unknown action: {action}. Use 'get', 'set', or 'clear'"}
        
        except Exception as e:
            log.error(f"Clipboard operation error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Clipboard operation failed: {e}"}

    # --- Screen Information Tools (Token-Efficient, No Screenshots) ---

    def get_screen_info(self, window_title: Optional[str] = None, max_depth: int = 3, 
                       include_invisible: bool = False) -> Dict[str, Any]:
        """
        Gets structured information about screen elements using UI Automation.
        This is much more token-efficient than screenshots and provides lossless information.
        
        Args:
            window_title: Optional window title to focus on (partial match). If None, uses active window.
            max_depth: Maximum depth to traverse the UI tree (default: 3)
            include_invisible: Whether to include invisible elements (default: False)
        
        Returns:
            Dict with status and structured UI information (element tree, text content, controls)
        """
        if auto is None:
            return {"status": "error", "message": "UI Automation not available. Install with: pip install uiautomation"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            # Get target window
            if window_title:
                # Find window by title
                window = auto.WindowControl(searchDepth=1, SubName=window_title)
                if not window.Exists(0, 0):
                    return {"status": "error", "message": f"Window with title '{window_title}' not found"}
            else:
                # Get active window
                window = auto.GetForegroundControl()
                if not window:
                    return {"status": "error", "message": "No active window found"}
            
            # Extract window information
            window_info = {
                "title": window.Name,
                "class_name": window.ClassName,
                "control_type": window.ControlTypeName,
                "bounds": {
                    "left": window.BoundingRectangle.left,
                    "top": window.BoundingRectangle.top,
                    "right": window.BoundingRectangle.right,
                    "bottom": window.BoundingRectangle.bottom,
                    "width": window.BoundingRectangle.width(),
                    "height": window.BoundingRectangle.height()
                }
            }
            
            # Extract UI tree structure
            def extract_element_info(element, current_depth=0):
                """Recursively extract element information"""
                if current_depth > max_depth:
                    return None
                
                # Check visibility - try multiple methods
                is_visible = True
                try:
                    # Check if element is off-screen (width/height <= 0)
                    if element.BoundingRectangle.width() <= 0 or element.BoundingRectangle.height() <= 0:
                        is_visible = False
                    # Check if element is enabled (often correlates with visibility)
                    if not element.IsEnabled:
                        is_visible = False
                except:
                    pass
                
                # Skip invisible elements if requested
                if not include_invisible and not is_visible:
                    return None
                
                info = {
                    "type": element.ControlTypeName,
                    "name": element.Name,
                    "class": element.ClassName,
                    "enabled": element.IsEnabled,
                    "visible": is_visible,
                    "bounds": {
                        "x": element.BoundingRectangle.left,
                        "y": element.BoundingRectangle.top,
                        "width": element.BoundingRectangle.width(),
                        "height": element.BoundingRectangle.height()
                    }
                }
                
                # Add automation ID if available
                if hasattr(element, 'AutomationId') and element.AutomationId:
                    info["automation_id"] = element.AutomationId
                
                # Add value for input controls
                if hasattr(element, 'GetValuePattern'):
                    try:
                        value_pattern = element.GetValuePattern()
                        if value_pattern:
                            info["value"] = value_pattern.Value
                    except:
                        pass
                
                # Add text for text controls
                if hasattr(element, 'GetTextPattern'):
                    try:
                        text_pattern = element.GetTextPattern()
                        if text_pattern:
                            info["text"] = text_pattern.DocumentRange.GetText(-1)
                    except:
                        pass
                
                # Get children
                children = []
                try:
                    for child in element.GetChildren():
                        child_info = extract_element_info(child, current_depth + 1)
                        if child_info:
                            children.append(child_info)
                except:
                    pass
                
                if children:
                    info["children"] = children
                
                return info
            
            # Extract UI tree
            ui_tree = extract_element_info(window, 0)
            
            # Extract all visible text from the window
            all_text = []
            def collect_text(element):
                """Recursively collect all text from elements"""
                try:
                    if element.Name and element.Name.strip():
                        all_text.append(element.Name)
                    
                    # Try to get text content
                    if hasattr(element, 'GetTextPattern'):
                        try:
                            text_pattern = element.GetTextPattern()
                            if text_pattern:
                                text_content = text_pattern.DocumentRange.GetText(-1)
                                if text_content and text_content.strip():
                                    all_text.append(text_content)
                        except:
                            pass
                    
                    for child in element.GetChildren():
                        collect_text(child)
                except:
                    pass
            
            collect_text(window)
            
            # Extract clickable elements (buttons, links, menu items)
            clickable_elements = []
            def find_clickable(element, path=""):
                """Find all clickable elements"""
                try:
                    element_type = element.ControlTypeName
                    if element_type in ["ButtonControl", "HyperlinkControl", "MenuItemControl", 
                                       "TabItemControl", "ListItemControl"]:
                        clickable_elements.append({
                            "type": element_type,
                            "name": element.Name,
                            "path": path,
                            "bounds": {
                                "x": element.BoundingRectangle.left,
                                "y": element.BoundingRectangle.top,
                                "width": element.BoundingRectangle.width(),
                                "height": element.BoundingRectangle.height()
                            },
                            "enabled": element.IsEnabled
                        })
                    
                    for i, child in enumerate(element.GetChildren()):
                        find_clickable(child, f"{path}/{element.ControlTypeName}[{i}]")
                except:
                    pass
            
            find_clickable(window)
            
            # Extract input fields
            input_fields = []
            def find_inputs(element):
                """Find all input fields"""
                try:
                    element_type = element.ControlTypeName
                    if element_type in ["EditControl", "TextControl", "ComboBoxControl"]:
                        field_info = {
                            "type": element_type,
                            "name": element.Name,
                            "class": element.ClassName,
                            "bounds": {
                                "x": element.BoundingRectangle.left,
                                "y": element.BoundingRectangle.top
                            },
                            "enabled": element.IsEnabled
                        }
                        
                        # Try to get current value
                        try:
                            value_pattern = element.GetValuePattern()
                            if value_pattern:
                                field_info["value"] = value_pattern.Value
                        except:
                            pass
                        
                        input_fields.append(field_info)
                    
                    for child in element.GetChildren():
                        find_inputs(child)
                except:
                    pass
            
            find_inputs(window)
            
            return {
                "status": "success",
                "window": window_info,
                "ui_tree": ui_tree,
                "text_content": list(set(all_text)),  # Remove duplicates
                "clickable_elements": clickable_elements,
                "input_fields": input_fields,
                "element_count": len(clickable_elements) + len(input_fields)
            }
        
        except Exception as e:
            log.error(f"Screen info extraction error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Failed to get screen info: {e}"}

    def find_ui_element(self, element_type: Optional[str] = None, name: Optional[str] = None,
                       class_name: Optional[str] = None, automation_id: Optional[str] = None,
                       window_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Finds specific UI elements on the screen for interaction.
        
        Args:
            element_type: Type of element (e.g., "ButtonControl", "EditControl", "TextControl")
            name: Name/label of the element (partial match)
            class_name: Windows class name
            automation_id: Automation ID of the element
            window_title: Optional window title to search within
        
        Returns:
            Dict with status and list of matching elements with their locations
        """
        if auto is None:
            return {"status": "error", "message": "UI Automation not available. Install with: pip install uiautomation"}
        
        if platform.system() != "Windows":
            return {"status": "error", "message": "This feature is only available on Windows."}
        
        try:
            # Get search root
            if window_title:
                root = auto.WindowControl(searchDepth=1, SubName=window_title)
                if not root.Exists(0, 0):
                    return {"status": "error", "message": f"Window '{window_title}' not found"}
            else:
                root = auto.GetForegroundControl()
                if not root:
                    return {"status": "error", "message": "No active window found"}
            
            # Build search criteria
            search_kwargs = {}
            if name:
                search_kwargs['SubName'] = name
            if class_name:
                search_kwargs['ClassName'] = class_name
            if automation_id:
                search_kwargs['AutomationId'] = automation_id
            
            # Search for elements
            found_elements = []
            
            def search_element(element, depth=0):
                """Recursively search for matching elements"""
                if depth > 10:  # Limit depth to prevent infinite loops
                    return
                
                try:
                    # Check if element matches criteria
                    matches = True
                    if element_type and element.ControlTypeName != element_type:
                        matches = False
                    if name and name.lower() not in element.Name.lower():
                        matches = False
                    if class_name and element.ClassName != class_name:
                        matches = False
                    if automation_id and hasattr(element, 'AutomationId') and element.AutomationId != automation_id:
                        matches = False
                    
                    if matches and element.IsEnabled:
                        element_info = {
                            "type": element.ControlTypeName,
                            "name": element.Name,
                            "class": element.ClassName,
                            "bounds": {
                                "x": element.BoundingRectangle.left,
                                "y": element.BoundingRectangle.top,
                                "width": element.BoundingRectangle.width(),
                                "height": element.BoundingRectangle.height(),
                                "center_x": element.BoundingRectangle.left + element.BoundingRectangle.width() // 2,
                                "center_y": element.BoundingRectangle.top + element.BoundingRectangle.height() // 2
                            },
                            "enabled": element.IsEnabled,
                            "visible": element.IsEnabled  # Simplified visibility check
                        }
                        
                        if hasattr(element, 'AutomationId') and element.AutomationId:
                            element_info["automation_id"] = element.AutomationId
                        
                        # Try to get value if it's an input control
                        try:
                            value_pattern = element.GetValuePattern()
                            if value_pattern:
                                element_info["value"] = value_pattern.Value
                        except:
                            pass
                        
                        found_elements.append(element_info)
                    
                    # Search children
                    for child in element.GetChildren():
                        search_element(child, depth + 1)
                except:
                    pass
            
            search_element(root)
            
            return {
                "status": "success",
                "found": len(found_elements),
                "elements": found_elements,
                "message": f"Found {len(found_elements)} matching element(s)"
            }
        
        except Exception as e:
            log.error(f"UI element search error: {traceback.format_exc()}")
            return {"status": "error", "message": f"Failed to find UI element: {e}"}

class AgentExecutor:
    def __init__(self):
        self.iteration_count = 0
        # Initialize managers. SessionManager will auto-start the default session.
        self.job_manager = JobManager()
        self.session_manager = SessionManager()
        self.toolbelt = Toolbelt(self)
        self.is_configured = True

    def execute_command(self, command_data: Dict[str, Any]) -> Dict[str, Any]:
        self.iteration_count += 1
        command, args = command_data.get('command'), command_data.get('args', {})
        
        log.info(f"Iteration {self.iteration_count} | Command: {command}")
        log.info(f"AI Thought: {command_data.get('thought', 'N/A')}")
        
        if command not in self.toolbelt.tools: 
            return {"status": "error", "message": f"Unknown command: '{command}'."}
        
        try:
            # Execute the tool
            result = self.toolbelt.tools[command](**args)
            if not isinstance(result, dict):
                result = {"status": "success", "data": result}
            result["iteration"] = self.iteration_count
            return result
        except TypeError as e:
            # Catch errors related to incorrect arguments
            log.error(f"Invalid arguments for command '{command}': {e}\n{traceback.format_exc()}")
            return {"status": "error", "message": f"Invalid arguments provided: {e}", "iteration": self.iteration_count}
        except Exception as e:
            # Catches runtime errors within the tool
            log.error(f"Error during command execution: {traceback.format_exc()}")
            return {"status": "error", "message": f"An internal error occurred: {e}", "iteration": self.iteration_count}

# === Web Server Implementation ===
# Initialize the executor globally
agent_executor = None
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": Config.ALLOWED_CORS_ORIGINS}})

@app.before_request
def check_auth():
    # Authentication/Authorization logic
    if request.method == 'OPTIONS':
        return # Skip auth for CORS preflight

    # 1. Shutdown endpoint: Must be localhost AND have the key
    if request.path == '/shutdown':
        if request.remote_addr not in ('127.0.0.1', 'localhost', '::1'):
             return jsonify({"status": "error", "message": "Forbidden: Shutdown allowed only from localhost"}), 403
        
        api_key = request.headers.get('X-API-Key')
        if api_key != Config.API_SECRET_KEY:
             return jsonify({"status": "error", "message": "Forbidden: Invalid API Key for shutdown"}), 403
        return

    # 2. API endpoints
    if request.path.startswith('/api/'):
        if request.path == '/api/status':
            return # Allow status check without auth (optional, depending on requirements)

        api_key = request.headers.get('X-API-Key')
        if api_key != Config.API_SECRET_KEY:
            return jsonify({"status": "error", "message": "Forbidden: Invalid API Key"}), 403

@app.route('/shutdown', methods=['POST'])
def shutdown():
    # Authorization handled by check_auth
    log.info("Shutdown command received from launcher. Shutting down server.")
    
    # --- FIX ---
    # Get the shutdown function from the request context *now*, in the main thread.
    shutdown_func = request.environ.get('werkzeug.server.shutdown')

    # Define a function to shut down Werkzeug server gracefully
    def shutdown_server(func): # <-- Pass the function in
        if func is None:
            # Fallback for non-Werkzeug servers (like Gunicorn)
            log.warning("Server environment does not support graceful shutdown via request. Terminating process.")
            import signal
            os.kill(os.getpid(), signal.SIGTERM)
            return
        
        # Call the passed-in function
        log.info("Calling werkzeug.server.shutdown...")
        func() # <-- Call the function that was passed
        
    # Execute shutdown in a thread to allow the response to be sent back
    # Pass the shutdown_func as an argument to the thread's target
    threading.Thread(target=shutdown_server, args=(shutdown_func,)).start()
    # --- END FIX ---
    
    return jsonify(status='success', message='Server is shutting down.')

@app.route('/api/execute_command', methods=['POST'])
def execute_command_endpoint():
    # Robust parsing logic
    command_data = request.get_json(silent=True)
    if command_data is None:
        try:
            raw_data = request.get_data(as_text=True)
            # Look for JSON block or plain JSON
            match = re.search(r'```json\s*(\{.*?\})\s*```|(\{.*?\})', raw_data, re.DOTALL)
            if match:
                command_data = json.loads(match.group(1) or match.group(2))
        except Exception as e:
            log.error(f"Robust parsing failed: {e}.")
            return jsonify({"status": "error", "message": "Failed to parse JSON."}), 400
            
    if command_data is None: 
        return jsonify({"status": "error", "message": "Failed to parse command."}), 400
    
    if agent_executor:
        return jsonify(agent_executor.execute_command(command_data))
    else:
        return jsonify({"status": "error", "message": "Server initialization failed."}), 500

@app.route('/api/status', methods=['GET'])
def api_status_endpoint():
    if agent_executor:
        return jsonify({
            "status": "running", 
            "version": "6.0.0",
            "configured": agent_executor.is_configured, 
            "sessions": list(agent_executor.session_manager.sessions.keys()),
            "default_session": agent_executor.session_manager.default_session_id,
            "platform": platform.system()
        })
    else:
         return jsonify({"status": "error", "message": "Server initialization failed."}), 500

def start_server():
    global agent_executor
    try:
        # Initialize the executor (this also starts the default session)
        agent_executor = AgentExecutor()

        if agent_executor.is_configured:
            log.info("--- AgentServer V6.0 (WSL/Process Management) successfully started! ---")
            # Run the Flask app. Debug and reloader MUST be False when managed by the launcher.
            app.run(host=Config.SERVER_HOST, port=Config.SERVER_PORT, debug=False, use_reloader=False)
        else:
            log.error("Startup failed: Configuration error.")
            sys.exit(1)
            
    except Exception as e:
        log.critical(f"A critical error occurred during server startup: {e}", exc_info=True)
        sys.exit(1) # Exit with error code so the launcher detects the failure
    finally:
        # Cleanup resources when the server stops
        log.info("Server shutting down. Cleaning up resources...")
        if agent_executor:
            agent_executor.session_manager.close_all()
        executor_pool.shutdown(wait=True)
        log.info("All active sessions terminated and thread pool shut down.")

if __name__ == "__main__":
    start_server()