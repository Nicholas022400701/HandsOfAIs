#!/usr/bin/env python3
"""
Test script for Windows system-level automation features.
This script tests the new automation capabilities added to AgentServer.

Note: This is a manual test script. Run it on a Windows machine to verify functionality.
"""

import requests
import json
import time
import sys
import os

# Configuration - use environment variable or fallback to default
SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://127.0.0.1:5005")
API_KEY = os.getenv("AGENT_API_KEY", "E8b2a1a2e9b1f0c1d1a9E8FF7aka55riotr0knlMMNF6a7b8c9d0e1f2a3b4c5d6e7f8a9b0")

def send_command(command, args, thought="Test command"):
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
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            return {"status": "error", "message": f"HTTP {response.status_code}: {response.text}"}
    except requests.exceptions.ConnectionError:
        return {"status": "error", "message": "Cannot connect to server. Is AgentServer running?"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def test_server_status():
    """Test if server is running"""
    print("=" * 60)
    print("Testing Server Status")
    print("=" * 60)
    try:
        response = requests.get(f"{SERVER_URL}/api/status", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Server is running")
            print(f"  Version: {data.get('version')}")
            print(f"  Platform: {data.get('platform')}")
            print(f"  Configured: {data.get('configured')}")
            return True
        else:
            print(f"✗ Server returned status code {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Cannot connect to server: {e}")
        print("\nPlease start the server first:")
        print("  python launcher.py")
        return False

def test_screen_capture():
    """Test screen capture functionality"""
    print("\n" + "=" * 60)
    print("Testing Screen Capture")
    print("=" * 60)
    
    # Test 1: Capture full screen (base64 only, no file save to avoid clutter)
    print("\nTest 1: Capture full screen")
    result = send_command("capture_screen", {"return_base64": False}, "Capture full screen")
    if result.get("status") == "success":
        print(f"✓ Screen captured successfully")
    else:
        print(f"✗ Failed: {result.get('message')}")
    
    # Test 2: Capture and save to file
    print("\nTest 2: Capture and save to file")
    result = send_command("capture_screen", {
        "filename": "test_screenshot.png",
        "return_base64": False
    }, "Capture and save to file")
    if result.get("status") == "success":
        print(f"✓ Screen captured and saved to: {result.get('saved_to')}")
    else:
        print(f"✗ Failed: {result.get('message')}")
    
    # Test 3: Capture specific region
    print("\nTest 3: Capture specific region (top-left 800x600)")
    result = send_command("capture_screen", {
        "region": "0,0,800,600",
        "return_base64": False
    }, "Capture region")
    if result.get("status") == "success":
        print(f"✓ Region captured successfully")
    else:
        print(f"✗ Failed: {result.get('message')}")

def test_keyboard_simulation():
    """Test keyboard simulation"""
    print("\n" + "=" * 60)
    print("Testing Keyboard Simulation")
    print("=" * 60)
    print("\nNote: These tests will actually type on your system!")
    print("Make sure you have a text editor or notepad open and focused.")
    input("Press Enter to continue or Ctrl+C to skip...")
    
    # Test 1: Press single key
    print("\nTest 1: Press Enter key")
    result = send_command("simulate_keyboard", {
        "action": "press",
        "key": "enter"
    }, "Press enter key")
    if result.get("status") == "success":
        print(f"✓ {result.get('message')}")
    else:
        print(f"✗ Failed: {result.get('message')}")
    time.sleep(0.5)
    
    # Test 2: Type text
    print("\nTest 2: Type text")
    result = send_command("simulate_keyboard", {
        "action": "type",
        "text": "Hello from AI automation test!",
        "interval": 0.05
    }, "Type text")
    if result.get("status") == "success":
        print(f"✓ {result.get('message')}")
    else:
        print(f"✗ Failed: {result.get('message')}")

def test_mouse_simulation():
    """Test mouse simulation"""
    print("\n" + "=" * 60)
    print("Testing Mouse Simulation")
    print("=" * 60)
    
    # Test 1: Get current position
    print("\nTest 1: Get current mouse position")
    result = send_command("simulate_mouse", {
        "action": "position"
    }, "Get mouse position")
    if result.get("status") == "success":
        pos = result.get("position", {})
        print(f"✓ Current position: ({pos.get('x')}, {pos.get('y')})")
    else:
        print(f"✗ Failed: {result.get('message')}")
    
    # Test 2: Move mouse
    print("\nTest 2: Move mouse to (500, 500)")
    print("Watch your mouse cursor move!")
    result = send_command("simulate_mouse", {
        "action": "move",
        "x": 500,
        "y": 500,
        "duration": 1.0
    }, "Move mouse")
    if result.get("status") == "success":
        print(f"✓ {result.get('message')}")
    else:
        print(f"✗ Failed: {result.get('message')}")
    time.sleep(1)

def test_window_management():
    """Test window management"""
    print("\n" + "=" * 60)
    print("Testing Window Management")
    print("=" * 60)
    
    # Test 1: List all windows
    print("\nTest 1: List all windows")
    result = send_command("get_windows", {
        "action": "list"
    }, "List windows")
    if result.get("status") == "success":
        windows = result.get("windows", [])
        print(f"✓ Found {len(windows)} windows:")
        for i, win in enumerate(windows[:5]):  # Show first 5
            print(f"  {i+1}. {win.get('title')[:50]}")
        if len(windows) > 5:
            print(f"  ... and {len(windows) - 5} more")
    else:
        print(f"✗ Failed: {result.get('message')}")

def test_clipboard_operations():
    """Test clipboard operations"""
    print("\n" + "=" * 60)
    print("Testing Clipboard Operations")
    print("=" * 60)
    
    # Test 1: Get current clipboard
    print("\nTest 1: Get current clipboard content")
    result = send_command("clipboard_operations", {
        "action": "get"
    }, "Get clipboard")
    if result.get("status") == "success":
        content = result.get("content", "")
        print(f"✓ Clipboard content ({len(content)} chars): {content[:50]}...")
    else:
        print(f"✗ Failed: {result.get('message')}")
    
    # Test 2: Set clipboard
    print("\nTest 2: Set clipboard content")
    test_text = "This is a test from HandsOfAIs automation!"
    result = send_command("clipboard_operations", {
        "action": "set",
        "text": test_text
    }, "Set clipboard")
    if result.get("status") == "success":
        print(f"✓ {result.get('message')}")
        
        # Verify by reading it back
        result = send_command("clipboard_operations", {"action": "get"}, "Verify clipboard")
        if result.get("content") == test_text:
            print(f"✓ Verified: Clipboard content matches")
        else:
            print(f"⚠ Warning: Clipboard content doesn't match")
    else:
        print(f"✗ Failed: {result.get('message')}")
    
    # Test 3: Clear clipboard
    print("\nTest 3: Clear clipboard")
    result = send_command("clipboard_operations", {
        "action": "clear"
    }, "Clear clipboard")
    if result.get("status") == "success":
        print(f"✓ {result.get('message')}")
    else:
        print(f"✗ Failed: {result.get('message')}")

def main():
    print("HandsOfAIs - Windows Automation Test Suite")
    print("=" * 60)
    print("\nThis script will test the new Windows automation features.")
    print("Some tests will control your keyboard and mouse!")
    print("\nMake sure:")
    print("  1. The AgentServer is running (python launcher.py)")
    print("  2. You are on a Windows machine")
    print("  3. You have a text editor open for keyboard tests")
    print("\n" + "=" * 60)
    
    input("\nPress Enter to start tests or Ctrl+C to cancel...")
    
    # Test server status first
    if not test_server_status():
        print("\n✗ Cannot proceed without server connection")
        sys.exit(1)
    
    # Run all tests
    try:
        test_screen_capture()
        test_clipboard_operations()
        test_window_management()
        test_mouse_simulation()
        
        # Keyboard test is interactive, ask first
        print("\n" + "=" * 60)
        response = input("\nRun keyboard simulation test? (y/n): ")
        if response.lower() == 'y':
            test_keyboard_simulation()
        else:
            print("Skipped keyboard simulation test")
        
        print("\n" + "=" * 60)
        print("All tests completed!")
        print("=" * 60)
        
    except KeyboardInterrupt:
        print("\n\nTests interrupted by user")
    except Exception as e:
        print(f"\n\n✗ Test suite error: {e}")

if __name__ == "__main__":
    main()
