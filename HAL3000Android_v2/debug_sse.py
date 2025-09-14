#!/usr/bin/env python3
"""
Debug SSE Stream from Device Hardware Bridge
"""

import requests
import json
from sseclient import SSEClient

def debug_sse_stream():
    """Debug the SSE stream to see what data we're actually getting"""
    
    print("=== DEBUG SSE STREAM ===")
    
    # Test basic connectivity
    try:
        response = requests.get("http://localhost:9999/health", timeout=5)
        print(f"✅ Hardware bridge health: {response.status_code}")
    except Exception as e:
        print(f"❌ Hardware bridge not accessible: {e}")
        return
    
    # Test SSE endpoint
    sse_url = "http://localhost:9999/api/device-screen/sse"
    headers = {"Accept": "text/event-stream"}
    
    print(f"Connecting to SSE stream: {sse_url}")
    
    try:
        with requests.get(sse_url, stream=True, headers=headers, timeout=10) as response:
            print(f"SSE Response status: {response.status_code}")
            print(f"SSE Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"❌ SSE endpoint failed: {response.text}")
                return
            
            print("✅ SSE stream connected, waiting for events...")
            
            event_source = (chunk for chunk in response.iter_content())
            client = SSEClient(event_source)
            
            event_count = 0
            for event in client.events():
                event_count += 1
                print(f"\n--- EVENT {event_count} ---")
                print(f"Event type: {event.event}")
                print(f"Event data length: {len(event.data) if event.data else 0}")
                
                if event.data:
                    try:
                        data = json.loads(event.data)
                        print(f"Data keys: {list(data.keys())}")
                        
                        elements = data.get("elements", [])
                        width = data.get("width", "N/A")
                        height = data.get("height", "N/A")
                        platform = data.get("platform", "N/A")
                        screenshot_path = data.get("screenshot", "N/A")
                        
                        print(f"Screenshot path: {screenshot_path}")
                        print(f"Elements count: {len(elements)}")
                        print(f"Screen size: {width}x{height}")
                        print(f"Platform: {platform}")
                        
                        if len(elements) > 0:
                            print(f"✅ FOUND UI ELEMENTS!")
                            print(f"First element: {elements[0]}")
                            
                            # Look for Settings elements
                            settings_elements = [e for e in elements if 'setting' in str(e).lower()]
                            print(f"Settings elements found: {len(settings_elements)}")
                            
                            if settings_elements:
                                print(f"Settings element: {settings_elements[0]}")
                        else:
                            print(f"❌ No UI elements in this event")
                            
                    except json.JSONDecodeError as e:
                        print(f"Failed to parse JSON: {e}")
                        print(f"Raw data: {event.data[:200]}...")
                
                # Stop after a few events to avoid infinite loop
                if event_count >= 3:
                    print(f"\nStopping after {event_count} events")
                    break
                    
    except requests.exceptions.Timeout:
        print("❌ SSE stream timeout - no events received")
    except Exception as e:
        print(f"❌ SSE stream error: {e}")

if __name__ == "__main__":
    debug_sse_stream()