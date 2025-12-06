# HandsOfAIs

A powerful system-level automation framework that enables AI agents to interact with Windows systems through screen capture, keyboard/mouse simulation, and window management.

## Features

### Original Features
- WSL/Local shell session management
- File system operations
- Command execution
- ArXiv paper search

### New Windows System-Level Automation Features
- **Screen Capture**: Capture screenshots of full screen, specific windows, or regions
- **Keyboard Simulation**: Type text, press keys, and execute hotkey combinations
- **Mouse Simulation**: Move cursor, click buttons, and scroll
- **Window Management**: List, activate, minimize, maximize, and close windows
- **Clipboard Operations**: Get, set, and clear clipboard content

## Installation

### Requirements
- Python 3.7+
- Windows OS (for system-level automation features)
- Optional: WSL (Windows Subsystem for Linux)

### Install Dependencies

```bash
pip install -r requirements.txt
```

For Windows system-level automation, ensure all optional dependencies are installed:
```bash
pip install pyautogui pillow pygetwindow pyperclip
```

## Usage

### Starting the Server

Run the launcher which manages the AgentServer:
```bash
python launcher.py
```

The server will start on `http://127.0.0.1:5005`

### API Endpoints

#### Execute Command
```
POST /api/execute_command
Headers: 
  X-API-Key: <your-api-key>
  Content-Type: application/json

Body:
{
  "command": "command_name",
  "args": {
    "param1": "value1"
  },
  "thought": "Optional AI reasoning"
}
```

### Available Commands

#### 1. Screen Capture (`capture_screen`)

Capture screenshots of your screen, specific windows, or regions.

```json
{
  "command": "capture_screen",
  "args": {
    "return_base64": true,
    "filename": "screenshot.png"
  }
}
```

Parameters:
- `region` (optional): Region as "x,y,width,height" (e.g., "100,100,800,600")
- `filename` (optional): Save screenshot to file in workspace
- `window_title` (optional): Capture specific window by title (partial match)
- `return_base64` (default: true): Return image as base64 string

**Example: Capture entire screen**
```json
{
  "command": "capture_screen",
  "args": {}
}
```

**Example: Capture specific window**
```json
{
  "command": "capture_screen",
  "args": {
    "window_title": "Chrome",
    "filename": "chrome_window.png"
  }
}
```

**Example: Capture region**
```json
{
  "command": "capture_screen",
  "args": {
    "region": "0,0,1920,1080"
  }
}
```

#### 2. Keyboard Simulation (`simulate_keyboard`)

Simulate keyboard input including typing, key presses, and hotkeys.

```json
{
  "command": "simulate_keyboard",
  "args": {
    "action": "type",
    "text": "Hello World"
  }
}
```

Parameters:
- `action`: "type", "press", or "hotkey"
- `text` (for type): Text to type
- `key` (for press): Single key name (e.g., "enter", "tab", "esc")
- `keys` (for hotkey): List of keys for combination (e.g., ["ctrl", "c"])
- `interval` (optional): Delay between keystrokes in seconds

**Example: Type text**
```json
{
  "command": "simulate_keyboard",
  "args": {
    "action": "type",
    "text": "Hello, AI!",
    "interval": 0.1
  }
}
```

**Example: Press single key**
```json
{
  "command": "simulate_keyboard",
  "args": {
    "action": "press",
    "key": "enter"
  }
}
```

**Example: Hotkey combination**
```json
{
  "command": "simulate_keyboard",
  "args": {
    "action": "hotkey",
    "keys": ["ctrl", "c"]
  }
}
```

#### 3. Mouse Simulation (`simulate_mouse`)

Control mouse movements, clicks, and scrolling.

```json
{
  "command": "simulate_mouse",
  "args": {
    "action": "click",
    "x": 500,
    "y": 300
  }
}
```

Parameters:
- `action`: "move", "click", "scroll", or "position"
- `x`, `y` (optional): Coordinates for move/click
- `button` (default: "left"): "left", "right", or "middle"
- `clicks` (default: 1): Number of clicks
- `duration` (default: 0.0): Movement duration in seconds

**Example: Get current position**
```json
{
  "command": "simulate_mouse",
  "args": {
    "action": "position"
  }
}
```

**Example: Move to position**
```json
{
  "command": "simulate_mouse",
  "args": {
    "action": "move",
    "x": 100,
    "y": 200,
    "duration": 1.0
  }
}
```

**Example: Click at position**
```json
{
  "command": "simulate_mouse",
  "args": {
    "action": "click",
    "x": 500,
    "y": 300,
    "button": "left",
    "clicks": 2
  }
}
```

**Example: Scroll**
```json
{
  "command": "simulate_mouse",
  "args": {
    "action": "scroll",
    "x": 10
  }
}
```

#### 4. Window Management (`get_windows`)

List and manage application windows.

```json
{
  "command": "get_windows",
  "args": {
    "action": "list"
  }
}
```

Parameters:
- `action`: "list", "activate", "minimize", "maximize", or "close"
- `title` (required for non-list actions): Window title (partial match)

**Example: List all windows**
```json
{
  "command": "get_windows",
  "args": {
    "action": "list"
  }
}
```

**Example: Activate window**
```json
{
  "command": "get_windows",
  "args": {
    "action": "activate",
    "title": "Chrome"
  }
}
```

**Example: Minimize window**
```json
{
  "command": "get_windows",
  "args": {
    "action": "minimize",
    "title": "Notepad"
  }
}
```

#### 5. Clipboard Operations (`clipboard_operations`)

Read from and write to the system clipboard.

```json
{
  "command": "clipboard_operations",
  "args": {
    "action": "get"
  }
}
```

Parameters:
- `action`: "get", "set", or "clear"
- `text` (for set): Text to copy to clipboard

**Example: Get clipboard content**
```json
{
  "command": "clipboard_operations",
  "args": {
    "action": "get"
  }
}
```

**Example: Set clipboard content**
```json
{
  "command": "clipboard_operations",
  "args": {
    "action": "set",
    "text": "Hello from AI!"
  }
}
```

**Example: Clear clipboard**
```json
{
  "command": "clipboard_operations",
  "args": {
    "action": "clear"
  }
}
```

## Security Considerations

1. **API Key**: The system uses an API key for authentication. Keep it secure.
2. **Windows-Only Features**: System-level automation is only available on Windows OS.
3. **Workspace Sandbox**: File operations are restricted to the workspace directory.
4. **Screen Capture**: Screenshots may contain sensitive information. Handle with care.

## Architecture

The system consists of:
1. **launcher.py**: Process manager that monitors and restarts the server
2. **AgentServer.py**: Main Flask server with automation tools
3. **Tampermonkey Script**: Browser integration for Gemini/AI Studio (optional)

## Configuration

Edit `AgentServer.py` to configure:
- `SERVER_HOST`: Server bind address (default: 127.0.0.1)
- `SERVER_PORT`: Server port (default: 5005)
- `API_SECRET_KEY`: Authentication key
- `WORKSPACE_DIR`: Working directory for file operations

## Troubleshooting

### PyAutoGUI Failsafe
PyAutoGUI has a failsafe feature - move your mouse to the top-left corner to abort automation if needed.

### Windows Permission Issues
Some applications may require administrator privileges for automation. Run as administrator if needed.

### Screen Capture Issues
- Ensure the target window is not minimized
- Some applications may block screen capture due to DRM protection

## License

This project is for educational and research purposes.