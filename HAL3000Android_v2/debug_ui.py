#!/usr/bin/env python3
"""
Debug UI Elements - Check what UI elements are actually available
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

from dotenv import load_dotenv
from minitap.mobile_use.context import MobileUseContext
from minitap.mobile_use.controllers.mobile_command_controller import get_screen_data

def debug_ui_elements():
    """Debug function to see all available UI elements using multiple methods"""
    
    # Load environment
    env_file = current_dir / ".env"
    if env_file.exists():
        load_dotenv(env_file)
        print(f"✓ Loaded configuration from {env_file}")
    
    try:
        # Method 1: Try the mobile-use way
        print("\n=== METHOD 1: Mobile-use API ===")
        from minitap.mobile_use.config import initialize_llm_config, settings
        from minitap.mobile_use.clients.screen_api_client import ScreenApiClient
        
        initialize_llm_config()
        screen_api_client = ScreenApiClient(
            base_url=settings.DEVICE_SCREEN_API_BASE_URL or "http://localhost:9998"
        )
        
        screen_data = get_screen_data(screen_api_client)
        print(f"Mobile-use API: {len(screen_data.elements)} elements")
        
        # Method 2: Direct API call to screen-info
        print("\n=== METHOD 2: Direct API Call ===")
        import requests
        try:
            response = requests.get("http://localhost:9998/screen-info", timeout=10)
            if response.status_code == 200:
                data = response.json()
                print(f"Direct API: {len(data.get('elements', []))} elements")
                print(f"API response structure: {list(data.keys())}")
            else:
                print(f"Direct API failed: {response.status_code}")
        except Exception as e:
            print(f"Direct API error: {e}")
        
        # Method 3: Try ADB UI dump
        print("\n=== METHOD 3: ADB UI Dump ===")
        import subprocess
        try:
            # Try uiautomator dump via ADB
            result = subprocess.run(['adb', 'shell', 'uiautomator', 'dump', '/sdcard/ui_dump.xml'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✓ ADB uiautomator dump successful")
                # Pull the file and check it
                pull_result = subprocess.run(['adb', 'pull', '/sdcard/ui_dump.xml', '.'], 
                                           capture_output=True, text=True, timeout=5)
                if pull_result.returncode == 0:
                    try:
                        with open('ui_dump.xml', 'r', encoding='utf-8') as f:
                            content = f.read()
                            print(f"✓ UI dump file size: {len(content)} characters")
                            # Count UI elements in the XML
                            element_count = content.count('<node ')
                            print(f"✓ Found {element_count} UI nodes in XML dump")
                            
                            # Look for Settings elements
                            if 'setting' in content.lower():
                                print("✓ Found 'setting' references in UI dump")
                            else:
                                print("❌ No 'setting' references in UI dump")
                                
                    except Exception as e:
                        print(f"Error reading UI dump: {e}")
                else:
                    print(f"Failed to pull UI dump: {pull_result.stderr}")
            else:
                print(f"ADB uiautomator dump failed: {result.stderr}")
        except Exception as e:
            print(f"ADB UI dump error: {e}")
        
        # Method 4: Check if Maestro is intercepting
        print("\n=== METHOD 4: Maestro Service Check ===")
        try:
            # Check if maestro daemon is running and blocking UI access
            response = requests.get("http://localhost:9998/health", timeout=5)
            print(f"Screen API health: {response.status_code}")
            
            response = requests.get("http://localhost:9999/health", timeout=5)
            print(f"Hardware bridge health: {response.status_code}")
            
        except Exception as e:
            print(f"Service health check error: {e}")
        
        # Method 5: Try alternative screen-info endpoints
        print("\n=== METHOD 5: Alternative Endpoints ===")
        endpoints = ["/screen-info", "/screenshot", "/ui-hierarchy", "/elements"]
        for endpoint in endpoints:
            try:
                response = requests.get(f"http://localhost:9998{endpoint}", timeout=5)
                print(f"{endpoint}: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, dict) and 'elements' in data:
                            print(f"  -> {len(data['elements'])} elements")
                    except:
                        print(f"  -> Non-JSON response")
            except Exception as e:
                print(f"{endpoint}: Error - {e}")
                
        # Method 6: Raw socket connection test
        print("\n=== METHOD 6: Socket Test ===")
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 9998))
            sock.close()
            if result == 0:
                print("✓ Port 9998 is accessible")
            else:
                print("❌ Port 9998 connection failed")
        except Exception as e:
            print(f"Socket test error: {e}")
                    
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    debug_ui_elements()