# Getting Started with HandsOfAIs Windows Automation

This guide will help you set up and use the new Windows system-level automation features.

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start the Server

```bash
python launcher.py
```

The server will start on `http://127.0.0.1:5005`

### 3. Test the System

Run the test suite to verify everything works:

```bash
python test_automation.py
```

Or run the token-efficiency demo:

```bash
python demo_token_efficient.py
```

## Key Concepts

### Token-Efficient Screen Understanding

**Traditional Approach (Expensive):**
- Take a screenshot → Convert to base64 → Send to AI
- Cost: 1000-5000 tokens per screen
- Problem: Loses structural information, AI must interpret pixels

**New Approach (Efficient):**
- Extract UI structure using Windows UI Automation
- Cost: 50-200 tokens per screen (20-100x cheaper!)
- Benefits: Preserves all information, direct element interaction

### Example Workflow

```python
import requests

# 1. Get screen information (token-efficient!)
result = requests.post("http://127.0.0.1:5005/api/execute_command", 
    headers={"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"},
    json={
        "command": "get_screen_info",
        "args": {}
    }
)

# 2. AI receives structured data:
# {
#   "window": {"title": "Notepad", "bounds": {...}},
#   "text_content": ["File", "Edit", "View", ...],
#   "clickable_elements": [
#     {"type": "ButtonControl", "name": "Save", "bounds": {"x": 100, "y": 50}}
#   ],
#   "input_fields": [...]
# }

# 3. AI can now interact precisely
requests.post("http://127.0.0.1:5005/api/execute_command",
    headers={"X-API-Key": "YOUR_API_KEY", "Content-Type": "application/json"},
    json={
        "command": "simulate_mouse",
        "args": {"action": "click", "x": 100, "y": 50}
    }
)
```

## Available Commands

### Primary Command: get_screen_info

**Use this instead of screenshots!**

```json
{
  "command": "get_screen_info",
  "args": {
    "window_title": "Chrome",  // optional, focuses on specific window
    "max_depth": 3,             // optional, UI tree depth
    "include_invisible": false  // optional, include hidden elements
  }
}
```

Returns:
- Window information
- Complete UI hierarchy
- All text content
- Clickable elements with positions
- Input fields with values

### Finding Specific Elements

```json
{
  "command": "find_ui_element",
  "args": {
    "element_type": "ButtonControl",  // optional: ButtonControl, EditControl, etc.
    "name": "Submit",                  // optional: element name (partial match)
    "window_title": "Chrome"           // optional: search in specific window
  }
}
```

### Keyboard Control

```json
// Type text
{
  "command": "simulate_keyboard",
  "args": {
    "action": "type",
    "text": "Hello World",
    "interval": 0.05  // delay between keystrokes
  }
}

// Press key
{
  "command": "simulate_keyboard",
  "args": {
    "action": "press",
    "key": "enter"
  }
}

// Hotkey combination
{
  "command": "simulate_keyboard",
  "args": {
    "action": "hotkey",
    "keys": ["ctrl", "c"]
  }
}
```

### Mouse Control

```json
// Get position
{
  "command": "simulate_mouse",
  "args": {"action": "position"}
}

// Move to position
{
  "command": "simulate_mouse",
  "args": {
    "action": "move",
    "x": 500,
    "y": 300,
    "duration": 1.0  // smooth movement over 1 second
  }
}

// Click
{
  "command": "simulate_mouse",
  "args": {
    "action": "click",
    "x": 500,
    "y": 300,
    "button": "left",  // left, right, or middle
    "clicks": 1         // number of clicks
  }
}

// Scroll
{
  "command": "simulate_mouse",
  "args": {
    "action": "scroll",
    "x": 10  // positive = scroll up, negative = scroll down
  }
}
```

### Window Management

```json
// List all windows
{
  "command": "get_windows",
  "args": {"action": "list"}
}

// Activate/focus window
{
  "command": "get_windows",
  "args": {
    "action": "activate",
    "title": "Chrome"  // partial match
  }
}

// Minimize/maximize/close
{
  "command": "get_windows",
  "args": {
    "action": "minimize",  // or "maximize", "close"
    "title": "Notepad"
  }
}
```

### Clipboard Operations

```json
// Get clipboard content
{
  "command": "clipboard_operations",
  "args": {"action": "get"}
}

// Set clipboard content
{
  "command": "clipboard_operations",
  "args": {
    "action": "set",
    "text": "Hello from AI!"
  }
}

// Clear clipboard
{
  "command": "clipboard_operations",
  "args": {"action": "clear"}
}
```

## Common Use Cases

### 1. Automated Form Filling

```python
# Get screen info to see available fields
result = send_command("get_screen_info", {})

# Find the username field
username_field = next(
    (f for f in result["input_fields"] if "username" in f["name"].lower()),
    None
)

if username_field:
    # Click the field
    send_command("simulate_mouse", {
        "action": "click",
        "x": username_field["bounds"]["x"],
        "y": username_field["bounds"]["y"]
    })
    
    # Type username
    send_command("simulate_keyboard", {
        "action": "type",
        "text": "myusername"
    })
```

### 2. Browser Automation

```python
# Activate browser window
send_command("get_windows", {
    "action": "activate",
    "title": "Chrome"
})

# Get screen info
info = send_command("get_screen_info", {})

# Find address bar
address_bar = next(
    (e for e in info["input_fields"] if "address" in e["name"].lower()),
    None
)

if address_bar:
    # Click address bar
    send_command("simulate_mouse", {
        "action": "click",
        "x": address_bar["bounds"]["x"],
        "y": address_bar["bounds"]["y"]
    })
    
    # Type URL
    send_command("simulate_keyboard", {
        "action": "type",
        "text": "https://example.com"
    })
    
    # Press Enter
    send_command("simulate_keyboard", {
        "action": "press",
        "key": "enter"
    })
```

### 3. Data Extraction

```python
# Get all text from a window
info = send_command("get_screen_info", {
    "window_title": "MyApp"
})

# Extract text content
all_text = info["text_content"]
print("Found text:", all_text)

# Extract all buttons
buttons = [
    e for e in info["clickable_elements"]
    if e["type"] == "ButtonControl"
]
print("Found buttons:", [b["name"] for b in buttons])
```

## Environment Variables

For security, set API key via environment variable:

```bash
# Windows
set AGENT_API_KEY=your_secret_key_here

# Linux/Mac
export AGENT_API_KEY=your_secret_key_here
```

Then use in scripts:

```python
import os
API_KEY = os.getenv("AGENT_API_KEY")
```

## Troubleshooting

### PyAutoGUI Failsafe
If automation goes wrong, move your mouse to the top-left corner to trigger the failsafe.

### UI Automation Not Finding Elements
- Ensure the window is not minimized
- Try increasing `max_depth` in `get_screen_info`
- Some applications have complex UI hierarchies

### Permission Issues
Some applications require administrator privileges. Run as admin if needed.

### Screenshots vs UI Automation
- Use `get_screen_info` for understanding and interaction (99% of cases)
- Use `capture_screen` only when you need visual verification
- Screenshots are expensive in tokens, use sparingly!

## Best Practices

1. **Always use `get_screen_info` first** - It's cheaper and better than screenshots
2. **Find elements by name** - More reliable than hardcoded coordinates
3. **Use `find_ui_element`** - For precise element location
4. **Activate windows** - Before interacting with them
5. **Add delays** - Between rapid actions for stability
6. **Handle errors** - Check response status before proceeding

## Integration with AI Models

The token-efficient approach works great with AI:

```python
# Get screen info (cheap!)
screen_info = send_command("get_screen_info", {})

# Send to AI with a prompt
prompt = f"""
Here's the current screen state:
{json.dumps(screen_info, indent=2)}

Task: Click the Submit button.
Provide the exact command to execute.
"""

# AI understands structured data much better than images!
# AI can reference exact elements by name/position
```

## Next Steps

1. Try the example scripts in `examples_automation.py`
2. Run the token efficiency demo: `demo_token_efficient.py`
3. Build your own automation workflows
4. Integrate with AI models for intelligent automation

For more information, see the main [README.md](README.md).
