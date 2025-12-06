import sys
import time
import logging
import subprocess
import shutil
import json
import os
import traceback
from pathlib import Path
import requests
import signal
import platform
import threading

# --- Configuration ---
# Ensure logs from both launcher and server are visible
logging.basicConfig(level=logging.INFO, format='%(asctime)s - [LAUNCHER] - %(levelname)s - %(message)s', stream=sys.stdout)

SERVER_SCRIPT_PATH = Path("AgentServer.py")
VERSIONS_DIR = Path("./versions")
COMMAND_FILE = Path("./launcher.cmd")
UPDATE_ERROR_LOG = Path("./update_error.log")
SERVER_PORT = 5005
# API Key for shutdown requests (must match AgentServer config)
API_KEY = 'E8b2a1a2e9b1f0c1d1a9E8FF7aka55riotr0knlMMNF6a7b8c9d0e1f2a3b4c5d6e7f8a9b0'

# --- Global State ---
server_process = None
state_lock = threading.Lock()
is_updating = False # Flag to prevent auto-restart during update

def stop_server_gracefully(timeout=15):
    """Attempts graceful shutdown via HTTP, then terminates the process group."""
    global server_process
    
    with state_lock:
        process = server_process
        if process is None or process.poll() is not None:
            logging.info("Server process is already stopped.")
            return

    pid = process.pid
    logging.info(f"Attempting graceful shutdown of PID {pid}...")

    # 1. Graceful shutdown via HTTP request
    try:
        url = f"http://127.0.0.1:{SERVER_PORT}/shutdown"
        headers = {'X-API-Key': API_KEY}
        requests.post(url, headers=headers, timeout=3)
    except requests.exceptions.RequestException:
        logging.warning("Shutdown request failed (server might be unresponsive).")

    # 2. Wait for exit (wait())
    try:
        process.wait(timeout=timeout/3)
        logging.info("Server process exited gracefully.")
        return
    except subprocess.TimeoutExpired:
        logging.warning("Server did not stop gracefully. Terminating (SIGTERM)...")

    # 3. Terminate (SIGTERM) - Ensure we kill the whole process group
    if platform.system() == "Windows":
        # On Windows, Popen with CREATE_NEW_PROCESS_GROUP allows simple terminate()
        process.terminate()
    else:
        # On Unix, we must kill the process group leader (PGID)
        try:
            os.killpg(os.getpgid(pid), signal.SIGTERM)
        except ProcessLookupError:
            pass # Process already dead

    # 4. Final Wait and Kill (SIGKILL)
    try:
        process.wait(timeout=timeout/3)
        logging.info("Server process terminated.")
    except subprocess.TimeoutExpired:
        logging.warning("Server did not terminate. Killing (SIGKILL)...")
        if platform.system() == "Windows":
            process.kill()
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
        process.wait(timeout=timeout/3)
    finally:
        with state_lock:
            if server_process == process:
                server_process = None

def start_server_process():
    """Starts the AgentServer.py as a new subprocess group. Returns None on success, or error string."""
    global server_process

    with state_lock:
        if server_process and server_process.poll() is None:
            logging.warning("Server process is already running.")
            return None
            
        try:
            if not SERVER_SCRIPT_PATH.exists():
                return f"Server script not found at {SERVER_SCRIPT_PATH.resolve()}."

            cmd = [sys.executable, str(SERVER_SCRIPT_PATH)]
            logging.info(f"Starting server process: {' '.join(cmd)}")
            
            # Configure process creation flags/hooks to ensure it runs in its own group
            kwargs = {}
            if platform.system() == "Windows":
                kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP
            else:
                # On Unix, setsid makes the new process the session leader and process group leader
                kwargs['preexec_fn'] = os.setsid

            # Start the process, inheriting stdout/stderr so logs are visible
            process = subprocess.Popen(cmd, stdout=sys.stdout, stderr=sys.stderr, **kwargs)
            server_process = process
            
            # Give the server time to start up or fail immediately (e.g., syntax errors)
            time.sleep(3)

            if process.poll() is None:
                logging.info(f"Server process started successfully (PID: {process.pid}).")
                return None # Success
            else:
                # Process terminated immediately
                return f"Server process terminated immediately with exit code {process.poll()}."

        except Exception:
            return traceback.format_exc()

def rollback(archive_path, error_details):
    """Rolls back to a previous version and logs the error."""
    logging.warning("--- INITIATING AUTOMATIC ROLLBACK ---")
    
    # Ensure the broken process is dead
    stop_server_gracefully(timeout=5)

    try:
        if not (archive_path and Path(archive_path).exists()):
            logging.critical(f"Rollback failed: Archive path '{archive_path}' not found!")
            return

        shutil.copy2(archive_path, SERVER_SCRIPT_PATH)
        logging.info(f"Successfully rolled back to version: {Path(archive_path).name}")

        # Write the error details for the AI feedback loop
        with open(UPDATE_ERROR_LOG, 'w', encoding='utf-8') as f:
            f.write(f"Update failed at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("The new version failed to start. Details:\n")
            f.write(error_details)
        logging.info(f"Update error details saved to '{UPDATE_ERROR_LOG}'.")

    except Exception as e:
        logging.critical(f"CRITICAL: Rollback process itself failed! System unstable. Error: {e}")

def manage_update(new_script_path_str: str):
    global is_updating

    with state_lock:
        if is_updating:
            logging.warning("Update already in progress.")
            return
        is_updating = True

    logging.info(f"--- Initiating Update from '{new_script_path_str}' ---")
    new_script_path = Path(new_script_path_str)

    # 1. Backup
    archive_path = None
    try:
        VERSIONS_DIR.mkdir(exist_ok=True)
        timestamp = time.strftime('%Y%m%d-%H%M%S')
        archive_path = VERSIONS_DIR / f"{SERVER_SCRIPT_PATH.stem}-{timestamp}{SERVER_SCRIPT_PATH.suffix}"
        shutil.copy2(SERVER_SCRIPT_PATH, archive_path)
        logging.info(f"Archived current version to '{archive_path}'.")
    except Exception as e:
        logging.error(f"CRITICAL: Failed to archive. Halting update. Error: {e}")
        with state_lock: is_updating = False
        return

    # 2. Stop current server
    stop_server_gracefully(timeout=15)
    
    # 3. Replace the file (shutil.copy2)
    try:
        logging.info(f"Replacing '{SERVER_SCRIPT_PATH}'...")
        shutil.copy2(new_script_path, SERVER_SCRIPT_PATH)
    except Exception as e:
        logging.error(f"Failed to replace server script. Attempting immediate rollback. Error: {e}")
        rollback(archive_path, f"File replacement failed: {e}")
        start_server_process() # Restart the old version
        with state_lock: is_updating = False
        return

    # 4. Start the new process and verify
    error_details = start_server_process()
    if error_details:
        # Startup failed, trigger rollback
        logging.error(f"Update failed: New version failed to start.")
        rollback(archive_path, error_details)
        
        # Restart the rolled-back version
        logging.info("Attempting to restart the rolled-back server version...")
        if start_server_process():
            logging.critical("CRITICAL: Failed to restart rolled-back version. System is down.")
    else:
        logging.info("--- Update successful. New version is running. ---")
    
    with state_lock: is_updating = False
    logging.info("--- Update process finished. ---")

def process_command_file():
    """Checks for and processes a command file."""
    if not COMMAND_FILE.exists():
        return
    
    # Prevent processing if an update is already underway
    with state_lock:
        if is_updating:
            logging.info("Command file detected, but update in progress. Skipping.")
            return

    logging.info("Command file found. Processing...")
    try:
        with open(COMMAND_FILE, 'r', encoding='utf-8') as f:
            cmd_data = json.load(f)
        
        if cmd_data.get('command') == 'update' and cmd_data.get('payload'):
            manage_update(cmd_data['payload'])
            
    except Exception as e:
        logging.error(f"Error processing command file: {e}", exc_info=True)
    finally:
        # Delete the file regardless of success/failure to prevent endless loops
        try:
            if COMMAND_FILE.exists():
                os.remove(COMMAND_FILE)
                logging.info("Command file processed and deleted.")
        except OSError as e:
            logging.error(f"Error deleting command file: {e}")

def monitor_server():
    """Monitors the server process and restarts it if it crashes unexpectedly."""
    with state_lock:
        if is_updating:
            return # Don't monitor during an expected shutdown/update

        if server_process is None:
            logging.warning("Server process not found outside update cycle. Attempting to start...")
            # Release lock before calling start_server_process as it acquires the lock
            state_lock.release()
            start_server_process()
            state_lock.acquire()
        elif server_process.poll() is not None:
            # Process has terminated unexpectedly
            logging.warning(f"Server process terminated unexpectedly (Exit Code: {server_process.poll()}). Restarting...")
            state_lock.release()
            start_server_process()
            state_lock.acquire()

if __name__ == "__main__":
    logging.info("Starting Launcher V6.0 (Subprocess Architecture).")

    # Initial Start
    if start_server_process():
        logging.critical("Initial server start failed. Exiting.")
        sys.exit(1)

    try:
        while True:
            process_command_file()
            monitor_server()
            time.sleep(3)
    except KeyboardInterrupt:
        logging.info("Launcher shutting down on user request (Ctrl+C).")
    finally:
        stop_server_gracefully()
        logging.info("Launcher shutdown complete.")