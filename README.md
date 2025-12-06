# HandsOfAIs

A powerful system-level automation framework that enables AI agents to interact with Windows systems through token-efficient screen information extraction, keyboard/mouse simulation, and window management.

## Features

### Original Features
- WSL/Local shell session management
- File system operations
- Command execution
- ArXiv paper search

### New Windows System-Level Automation Features
- **Token-Efficient Screen Information** (NEW!): Get structured UI information without screenshots - no token waste, lossless information
- **Screen Capture**: Capture screenshots of full screen, specific windows, or regions (optional, for when images are needed)
- **Keyboard Simulation**: Type text, press keys, and execute hotkey combinations
- **Mouse Simulation**: Move cursor, click buttons, and scroll
- **Window Management**: List, activate, minimize, maximize, and close windows
- **Clipboard Operations**: Get, set, and clear clipboard content
- **UI Element Discovery**: Find and interact with specific UI elements by name, type, or properties

## Why Token-Efficient Screen Information?

Traditional approaches use screenshots to let AI "see" the screen, but this has major drawbacks:
- **High token cost**: Images consume many tokens in AI models
- **Information loss**: Screenshots lose structured information about UI elements
- **No direct interaction**: Can't directly reference specific buttons or fields

Our solution uses **Windows UI Automation** to extract structured information:
- **Near-zero token cost**: Text-based UI tree structure
- **Lossless information**: Get exact element names, types, positions, and properties
- **Direct interaction**: Can click/type into specific elements by reference
- **Better for AI**: Structured JSON is easier for AI to understand than images

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
pip install pyautogui pillow pygetwindow pyperclip uiautomation
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

#### 1. Get Screen Information (`get_screen_info`) - **RECOMMENDED**

**Token-efficient way to understand screen content without screenshots!**

Gets structured information about UI elements on the screen using Windows UI Automation. This is much more efficient than screenshots and provides lossless, structured information.

```json
{
  "command": "get_screen_info",
  "args": {}
}
```

Parameters:
- `window_title` (optional): Focus on specific window (partial match). If None, uses active window.
- `max_depth` (default: 3): Maximum depth to traverse UI tree
- `include_invisible` (default: false): Include invisible elements

**Returns:**
- Window information (title, size, position)
- Complete UI element tree with hierarchy
- All visible text content
- List of clickable elements (buttons, links, etc.) with positions
- List of input fields with current values
- No image data - pure structured information!

**Example: Get info about active window**
```json
{
  "command": "get_screen_info",
  "args": {}
}
```

**Example: Get info about specific window**
```json
{
  "command": "get_screen_info",
  "args": {
    "window_title": "Chrome",
    "max_depth": 4
  }
}
```

**Response example:**
```json
{
  "status": "success",
  "window": {
    "title": "Google Chrome",
    "class_name": "Chrome_WidgetWin_1",
    "bounds": {"left": 0, "top": 0, "width": 1920, "height": 1080}
  },
  "text_content": ["File", "Edit", "View", "Search", "Hello World", ...],
  "clickable_elements": [
    {
      "type": "ButtonControl",
      "name": "Close",
      "bounds": {"x": 1880, "y": 10, "center_x": 1900, "center_y": 20},
      "enabled": true
    }
  ],
  "input_fields": [
    {
      "type": "EditControl",
      "name": "Address bar",
      "value": "https://google.com",
      "bounds": {"x": 100, "y": 50}
    }
  ]
}
```

#### 2. Find UI Element (`find_ui_element`)

Find specific UI elements for interaction. Use this to locate buttons, input fields, or other controls.

```json
{
  "command": "find_ui_element",
  "args": {
    "name": "Submit",
    "element_type": "ButtonControl"
  }
}
```

Parameters:
- `element_type` (optional): Type like "ButtonControl", "EditControl", "TextControl"
- `name` (optional): Element name/label (partial match)
- `class_name` (optional): Windows class name
- `automation_id` (optional): Automation ID
- `window_title` (optional): Search within specific window

**Example: Find a button**
```json
{
  "command": "find_ui_element",
  "args": {
    "name": "Submit",
    "element_type": "ButtonControl"
  }
}
```

**Example: Find all input fields**
```json
{
  "command": "find_ui_element",
  "args": {
    "element_type": "EditControl"
  }
}
```

**Response includes:**
- Element type, name, and properties
- Exact position (x, y, width, height)
- Center coordinates for clicking
- Current value (for input fields)
- Enabled/visible status

#### 3. Screen Capture (`capture_screen`) - Optional

Capture screenshots when you really need images (e.g., for visual verification). 
**Note**: Use `get_screen_info` instead when possible to save tokens!

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

#### 4. Keyboard Simulation (`simulate_keyboard`)

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

#### 5. Mouse Simulation (`simulate_mouse`)

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

#### 6. Window Management (`get_windows`)

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

#### 7. Clipboard Operations (`clipboard_operations`)

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

## Workflow Examples

### Example 1: Token-Efficient Screen Understanding
Instead of sending screenshots, get structured information:

```json
// Step 1: Get screen info (costs ~100 tokens vs 1000+ for screenshot)
{
  "command": "get_screen_info",
  "args": {}
}

// AI receives structured data like:
// - "Submit" button at (100, 200)
// - "Username" input field with value ""
// - Text content: ["Login", "Username", "Password", "Submit"]

// Step 2: AI can now interact precisely
{
  "command": "find_ui_element",
  "args": {
    "name": "Username",
    "element_type": "EditControl"
  }
}

// Step 3: Click on the found element
{
  "command": "simulate_mouse",
  "args": {
    "action": "click",
    "x": 150,
    "y": 100
  }
}

// Step 4: Type into the field
{
  "command": "simulate_keyboard",
  "args": {
    "action": "type",
    "text": "myusername"
  }
}
```

### Example 2: Automated Form Filling
```json
// Get all input fields
{
  "command": "get_screen_info",
  "args": {"max_depth": 5}
}

// AI sees input_fields: [
//   {"name": "First Name", "bounds": {"x": 100, "y": 50}},
//   {"name": "Last Name", "bounds": {"x": 100, "y": 100}},
//   {"name": "Email", "bounds": {"x": 100, "y": 150}}
// ]

// Fill each field
{
  "command": "simulate_mouse",
  "args": {"action": "click", "x": 100, "y": 50}
}
{
  "command": "simulate_keyboard",
  "args": {"action": "type", "text": "John"}
}
// Repeat for other fields...
```

### Example 3: Browser Automation
```json
// Find browser address bar
{
  "command": "find_ui_element",
  "args": {
    "name": "Address",
    "element_type": "EditControl",
    "window_title": "Chrome"
  }
}

// Click address bar
{
  "command": "simulate_mouse",
  "args": {"action": "click", "x": 500, "y": 50}
}

// Type URL
{
  "command": "simulate_keyboard",
  "args": {
    "action": "type",
    "text": "https://example.com"
  }
}

// Press Enter
{
  "command": "simulate_keyboard",
  "args": {"action": "press", "key": "enter"}
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