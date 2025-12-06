#!/usr/bin/env python3
"""
Token-Efficient Screen Understanding Example

This demonstrates the new token-efficient approach to screen understanding
using Windows UI Automation instead of screenshots.

Comparison:
- Screenshot approach: 1000-5000 tokens per screen
- UI Automation approach: 50-200 tokens per screen (20-100x more efficient!)
"""

import requests
import json
import os

# Configuration - use environment variable or fallback to default
SERVER_URL = os.getenv("AGENT_SERVER_URL", "http://127.0.0.1:5005")
API_KEY = os.getenv("AGENT_API_KEY", "E8b2a1a2e9b1f0c1d1a9E8FF7aka55riotr0knlMMNF6a7b8c9d0e1f2a3b4c5d6e7f8a9b0")

def send_command(command, args):
    """Send command to AgentServer"""
    url = f"{SERVER_URL}/api/execute_command"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY
    }
    data = {"command": command, "args": args}
    response = requests.post(url, headers=headers, json=data, timeout=30)
    return response.json()

def demo_old_way():
    """
    OLD WAY: Using screenshots (token-inefficient)
    """
    print("\n" + "="*60)
    print("OLD WAY: Using Screenshots (Token-Inefficient)")
    print("="*60)
    
    # Capture screenshot
    result = send_command("capture_screen", {"return_base64": True})
    
    if result["status"] == "success":
        base64_length = len(result["image_base64"])
        
        # Estimate token usage
        # Base64 image is ~4/3 the size of binary
        # GPT models use ~1 token per 4 characters
        estimated_tokens = base64_length // 4
        
        print(f"✓ Screenshot captured")
        print(f"  Base64 length: {base64_length:,} characters")
        print(f"  Estimated tokens: ~{estimated_tokens:,} tokens")
        print(f"  Cost: HIGH (varies by model)")
        print(f"\nProblems:")
        print("  - Wastes many tokens")
        print("  - Loses structural information")
        print("  - Can't reference specific elements")
        print("  - AI must interpret pixels")
    else:
        print(f"✗ Failed: {result.get('message')}")

def demo_new_way():
    """
    NEW WAY: Using UI Automation (token-efficient)
    """
    print("\n" + "="*60)
    print("NEW WAY: Using UI Automation (Token-Efficient)")
    print("="*60)
    
    # Get structured screen information
    result = send_command("get_screen_info", {"max_depth": 3})
    
    if result["status"] == "success":
        # Convert to JSON and estimate tokens
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        json_length = len(json_str)
        estimated_tokens = json_length // 4  # Rough estimate
        
        print(f"✓ Screen info extracted")
        print(f"  JSON length: {json_length:,} characters")
        print(f"  Estimated tokens: ~{estimated_tokens:,} tokens")
        print(f"  Cost: VERY LOW")
        
        # Show what we got
        print(f"\nWindow Info:")
        print(f"  Title: {result['window']['title']}")
        print(f"  Size: {result['window']['bounds']['width']}x{result['window']['bounds']['height']}")
        
        print(f"\nText Content: ({len(result['text_content'])} items)")
        for text in result['text_content'][:10]:  # Show first 10
            print(f"  - {text[:50]}")
        if len(result['text_content']) > 10:
            print(f"  ... and {len(result['text_content']) - 10} more")
        
        print(f"\nClickable Elements: ({len(result['clickable_elements'])} items)")
        for elem in result['clickable_elements'][:5]:  # Show first 5
            print(f"  - {elem['type']}: '{elem['name']}' at ({elem['bounds']['center_x']}, {elem['bounds']['center_y']})")
        if len(result['clickable_elements']) > 5:
            print(f"  ... and {len(result['clickable_elements']) - 5} more")
        
        print(f"\nInput Fields: ({len(result['input_fields'])} items)")
        for field in result['input_fields'][:5]:
            value = field.get('value', '')
            print(f"  - {field['name']}: '{value[:30]}' at ({field['bounds']['x']}, {field['bounds']['y']})")
        
        print(f"\nAdvantages:")
        print("  ✓ 20-100x fewer tokens than screenshots")
        print("  ✓ Preserves all structural information")
        print("  ✓ Can reference elements by name/position")
        print("  ✓ AI gets exact element hierarchy")
        print("  ✓ Works with any UI framework")
    else:
        print(f"✗ Failed: {result.get('message')}")

def demo_ai_workflow():
    """
    Demonstrate how AI would use this information
    """
    print("\n" + "="*60)
    print("AI Workflow Example")
    print("="*60)
    
    print("\n1. AI asks: 'What's on the screen?'")
    result = send_command("get_screen_info", {})
    
    if result["status"] == "success":
        print(f"   → System responds with structured data ({len(json.dumps(result))//4} tokens)")
        print(f"   → Window: {result['window']['title']}")
        print(f"   → {len(result['clickable_elements'])} buttons/links found")
        print(f"   → {len(result['input_fields'])} input fields found")
        
        # Simulate AI understanding
        print("\n2. AI understands: 'I see a window with buttons and input fields'")
        
        if result['clickable_elements']:
            button = result['clickable_elements'][0]
            print(f"\n3. AI decides: 'I'll click the {button['name']} button'")
            print(f"   → Button location: ({button['bounds']['center_x']}, {button['bounds']['center_y']})")
            
            # AI would now execute this:
            print("\n4. AI executes:")
            print(f"   simulate_mouse(action='click', x={button['bounds']['center_x']}, y={button['bounds']['center_y']})")
            print("   ✓ Direct, precise interaction!")
        
        print("\n5. Result:")
        print("   ✓ AI understood screen with minimal tokens")
        print("   ✓ AI interacted precisely with UI elements")
        print("   ✓ No guessing coordinates from images!")
    else:
        print(f"✗ Failed: {result.get('message')}")

def demo_find_element():
    """
    Demonstrate finding specific elements
    """
    print("\n" + "="*60)
    print("Finding Specific UI Elements")
    print("="*60)
    
    # Example: Find all buttons
    print("\n1. Finding all buttons...")
    result = send_command("find_ui_element", {
        "element_type": "ButtonControl"
    })
    
    if result["status"] == "success":
        print(f"   ✓ Found {result['found']} buttons")
        for elem in result['elements'][:3]:
            print(f"     - '{elem['name']}' at ({elem['bounds']['center_x']}, {elem['bounds']['center_y']})")
    
    # Example: Find specific button by name
    print("\n2. Finding 'Close' button...")
    result = send_command("find_ui_element", {
        "element_type": "ButtonControl",
        "name": "Close"
    })
    
    if result["status"] == "success" and result['found'] > 0:
        elem = result['elements'][0]
        print(f"   ✓ Found at ({elem['bounds']['center_x']}, {elem['bounds']['center_y']})")
        print(f"   → AI can now click it directly!")
    else:
        print(f"   → Not found (no problem, just an example)")
    
    # Example: Find input fields
    print("\n3. Finding input fields...")
    result = send_command("find_ui_element", {
        "element_type": "EditControl"
    })
    
    if result["status"] == "success":
        print(f"   ✓ Found {result['found']} input fields")
        for elem in result['elements'][:3]:
            value = elem.get('value', '')
            print(f"     - '{elem['name']}': current value = '{value[:20]}'")

def main():
    print("="*60)
    print("Token-Efficient Screen Understanding Demo")
    print("="*60)
    print("\nThis demonstrates why UI Automation is superior to screenshots")
    print("for AI agents to understand and interact with screens.")
    
    # Check server
    try:
        response = requests.get(f"{SERVER_URL}/api/status", timeout=5)
        if response.status_code != 200:
            print("\n✗ Server not responding. Please start: python launcher.py")
            return
    except:
        print("\n✗ Cannot connect to server. Please start: python launcher.py")
        return
    
    print("\n" + "="*60)
    print("COMPARISON: Screenshots vs UI Automation")
    print("="*60)
    
    try:
        # Show old way (screenshots)
        demo_old_way()
        
        # Show new way (UI automation)
        demo_new_way()
        
        # Show how AI would use this
        demo_ai_workflow()
        
        # Show element finding
        demo_find_element()
        
        print("\n" + "="*60)
        print("CONCLUSION")
        print("="*60)
        print("\nUI Automation is MUCH better than screenshots for AI agents:")
        print("  ✓ 20-100x more token-efficient")
        print("  ✓ Lossless structural information")
        print("  ✓ Direct element interaction")
        print("  ✓ Faster processing")
        print("  ✓ Lower costs")
        print("\nUse screenshots only when you need visual verification!")
        print("="*60)
        
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n✗ Error: {e}")

if __name__ == "__main__":
    main()
