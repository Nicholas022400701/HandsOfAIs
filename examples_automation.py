#!/usr/bin/env python3
"""
Example usage of HandsOfAIs Windows automation capabilities.

This script demonstrates how to use the new system-level automation features
to create powerful AI-driven workflows.
"""

import requests
import json
import time
import base64
import os
from pathlib import Path

# Configuration - use environment variable or fallback to default
SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://127.0.0.1:5005")
API_KEY = os.getenv("AGENT_API_KEY", "E8b2a1a2e9b1f0c1d1a9E8FF7aka55riotr0knlMMNF6a7b8c9d0e1f2a3b4c5d6e7f8a9b0")

def send_command(command, args, thought=""):
    """Send a command to the AgentServer"""
    url = f"{SERVER_URL}/api/execute_command"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    data = {
        "command": command,
        "args": args,
        "thought": thought
    }
    
    response = requests.post(url, headers=headers, json=data, timeout=30)
    return response.json()

def example_1_screenshot_workflow():
    """
    Example 1: Screenshot Workflow
    Take a screenshot of the current screen and save it to a file.
    """
    print("\n=== Example 1: Screenshot Workflow ===")
    
    # Capture the entire screen and save to file
    result = send_command("capture_screen", {
        "filename": "my_screen.png",
        "return_base64": False  # Don't need base64 if just saving
    }, "Capture current screen state")
    
    if result["status"] == "success":
        print(f"✓ Screenshot saved to: {result['saved_to']}")
    else:
        print(f"✗ Failed: {result['message']}")

def example_2_window_screenshot():
    """
    Example 2: Capture Specific Window
    Find a window by title and capture only that window.
    """
    print("\n=== Example 2: Capture Specific Window ===")
    
    # First, list all windows to see what's available
    result = send_command("get_windows", {
        "action": "list"
    }, "Get list of open windows")
    
    if result["status"] == "success" and result["windows"]:
        print(f"Found {len(result['windows'])} windows")
        
        # Show first few windows
        for i, win in enumerate(result["windows"][:3]):
            print(f"  - {win['title']}")
        
        # Let's capture the first window with a non-empty title
        target_window = result["windows"][0]["title"]
        print(f"\nCapturing window: {target_window}")
        
        # Activate the window first
        activate_result = send_command("get_windows", {
            "action": "activate",
            "title": target_window
        }, "Bring window to front")
        
        time.sleep(0.5)  # Give window time to come to front
        
        # Capture the window
        capture_result = send_command("capture_screen", {
            "window_title": target_window,
            "filename": "captured_window.png"
        }, "Capture specific window")
        
        if capture_result["status"] == "success":
            print(f"✓ Window screenshot saved")
        else:
            print(f"✗ Failed: {capture_result['message']}")

def example_3_automated_notepad():
    """
    Example 3: Automated Text Entry
    Open notepad (if available) and write some text using keyboard automation.
    """
    print("\n=== Example 3: Automated Text Entry ===")
    print("Note: Make sure Notepad is open and focused!")
    input("Press Enter to continue...")
    
    # Type a message
    result = send_command("simulate_keyboard", {
        "action": "type",
        "text": "This text was typed by an AI agent!\n",
        "interval": 0.05
    }, "Type greeting message")
    
    if result["status"] == "success":
        print("✓ Text typed successfully")
        
        # Add a line break
        send_command("simulate_keyboard", {
            "action": "press",
            "key": "enter"
        })
        
        # Type more text
        send_command("simulate_keyboard", {
            "action": "type",
            "text": "I can control the keyboard and perform complex tasks!",
            "interval": 0.05
        })
        
        print("✓ Second line typed")
    else:
        print(f"✗ Failed: {result['message']}")

def example_4_clipboard_workflow():
    """
    Example 4: Clipboard Workflow
    Copy text to clipboard, simulate Ctrl+V to paste it.
    """
    print("\n=== Example 4: Clipboard Workflow ===")
    
    # Set clipboard content
    text_to_copy = "Hello from AI automation system!"
    result = send_command("clipboard_operations", {
        "action": "set",
        "text": text_to_copy
    }, "Copy text to clipboard")
    
    if result["status"] == "success":
        print(f"✓ Copied to clipboard: {text_to_copy}")
        
        # Now we can use Ctrl+V to paste this anywhere
        print("Ready to paste with Ctrl+V")
        print("(In a real workflow, you'd use simulate_keyboard with hotkey)")
        
        # Example: Simulate paste (make sure a text field is focused)
        # send_command("simulate_keyboard", {
        #     "action": "hotkey",
        #     "keys": ["ctrl", "v"]
        # })
    else:
        print(f"✗ Failed: {result['message']}")

def example_5_mouse_navigation():
    """
    Example 5: Mouse Navigation
    Get mouse position and move it around.
    """
    print("\n=== Example 5: Mouse Navigation ===")
    
    # Get current position
    result = send_command("simulate_mouse", {
        "action": "position"
    }, "Get current mouse position")
    
    if result["status"] == "success":
        pos = result["position"]
        print(f"Current mouse position: ({pos['x']}, {pos['y']})")
        
        # Move to center of typical screen
        print("Moving mouse to screen center...")
        send_command("simulate_mouse", {
            "action": "move",
            "x": 960,
            "y": 540,
            "duration": 1.0
        }, "Move to center")
        
        time.sleep(1)
        
        # Move back to original position
        print("Moving back to original position...")
        send_command("simulate_mouse", {
            "action": "move",
            "x": pos['x'],
            "y": pos['y'],
            "duration": 1.0
        }, "Return to original position")
        
        print("✓ Mouse navigation complete")

def example_6_ai_vision_workflow():
    """
    Example 6: AI Vision Workflow
    Demonstrates how to capture screen and prepare it for AI analysis.
    """
    print("\n=== Example 6: AI Vision Workflow ===")
    
    # Capture screen with base64 encoding
    result = send_command("capture_screen", {
        "return_base64": True
    }, "Capture screen for AI analysis")
    
    if result["status"] == "success":
        # In a real workflow, you would send this base64 image to an AI vision model
        # like GPT-4 Vision, Claude with vision, or Gemini Pro Vision
        img_base64 = result["image_base64"]
        img_size = result["image_size"]
        
        print(f"✓ Captured screen: {img_size['width']}x{img_size['height']}")
        print(f"  Base64 length: {len(img_base64)} characters")
        print("\nThis image can now be sent to AI vision models for analysis!")
        print("Example: 'What's on my screen?', 'Click the blue button', etc.")
        
        # Example pseudo-code for AI integration:
        # ai_response = send_to_vision_ai(img_base64, prompt="What do you see?")
        # print(f"AI sees: {ai_response}")
    else:
        print(f"✗ Failed: {result['message']}")

def example_7_complex_workflow():
    """
    Example 7: Complex Workflow
    Combine multiple automation features for a complex task.
    """
    print("\n=== Example 7: Complex Workflow ===")
    print("This example shows a complete workflow:")
    print("1. List windows")
    print("2. Capture current screen")
    print("3. Get clipboard content")
    print("4. Report findings")
    
    workflow_report = []
    
    # Step 1: List windows
    result = send_command("get_windows", {"action": "list"})
    if result["status"] == "success":
        window_count = len(result["windows"])
        workflow_report.append(f"Found {window_count} open windows")
        print(f"✓ Step 1: {workflow_report[-1]}")
    
    # Step 2: Capture screen
    result = send_command("capture_screen", {
        "filename": "workflow_screenshot.png",
        "return_base64": False
    })
    if result["status"] == "success":
        workflow_report.append(f"Screenshot saved to {result['saved_to']}")
        print(f"✓ Step 2: {workflow_report[-1]}")
    
    # Step 3: Get clipboard
    result = send_command("clipboard_operations", {"action": "get"})
    if result["status"] == "success":
        clip_len = len(result["content"])
        workflow_report.append(f"Clipboard contains {clip_len} characters")
        print(f"✓ Step 3: {workflow_report[-1]}")
    
    # Step 4: Report
    print("\n--- Workflow Report ---")
    for item in workflow_report:
        print(f"  • {item}")
    print("✓ Complex workflow completed successfully")

def main():
    print("=" * 60)
    print("HandsOfAIs - Windows Automation Examples")
    print("=" * 60)
    print("\nThese examples demonstrate the new system-level automation")
    print("capabilities that allow AI agents to 'see' and 'control'")
    print("your Windows desktop.")
    print("\nMake sure the AgentServer is running: python launcher.py")
    print("=" * 60)
    
    # Check server
    try:
        response = requests.get(f"{SERVER_URL}/api/status", timeout=5)
        if response.status_code != 200:
            print("\n✗ Server not responding. Please start it first.")
            return
        print("\n✓ Server is running")
    except Exception as e:
        print(f"\n✗ Cannot connect to server: {e}")
        print("Please start the server: python launcher.py")
        return
    
    # Run examples
    examples = [
        ("1", "Screenshot Workflow", example_1_screenshot_workflow),
        ("2", "Capture Specific Window", example_2_window_screenshot),
        ("3", "Automated Text Entry", example_3_automated_notepad),
        ("4", "Clipboard Workflow", example_4_clipboard_workflow),
        ("5", "Mouse Navigation", example_5_mouse_navigation),
        ("6", "AI Vision Workflow", example_6_ai_vision_workflow),
        ("7", "Complex Workflow", example_7_complex_workflow),
    ]
    
    print("\nAvailable examples:")
    for num, name, _ in examples:
        print(f"  {num}. {name}")
    print("  0. Run all examples")
    
    choice = input("\nSelect example (or press Enter to run all): ").strip()
    
    try:
        if choice == "" or choice == "0":
            # Run all examples
            for _, _, func in examples:
                func()
                time.sleep(1)
        else:
            # Run specific example
            example_num = int(choice) - 1
            if 0 <= example_num < len(examples):
                examples[example_num][2]()
            else:
                print("Invalid choice")
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")
    
    print("\n" + "=" * 60)
    print("Examples completed!")
    print("=" * 60)

if __name__ == "__main__":
    main()
