#!/usr/bin/env python3
"""
Diagnose Maestro/UI Automator Issues
"""

import subprocess
import requests

def check_maestro_status():
    """Check if Maestro is running and UI automator is working"""
    
    print("=== MAESTRO DIAGNOSTIC ===")
    
    # Check if maestro daemon is running
    try:
        result = subprocess.run(['maestro', 'test', '--help'], 
                              capture_output=True, text=True, timeout=5)
        print("✅ Maestro CLI is available")
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.CalledProcessError) as e:
        print(f"❌ Maestro CLI issue: {e}")
    
    # Check device screen API
    try:
        response = requests.get("http://localhost:9998/screen-info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Device Screen API responding")
            print(f"   Screenshot available: {'base64' in data}")
            print(f"   UI elements count: {len(data.get('elements', []))}")
            print(f"   Screen size: {data.get('width')}x{data.get('height')}")
            
            if len(data.get('elements', [])) == 0:
                print("❌ UI HIERARCHY EMPTY - This is the problem!")
                print("   Possible causes:")
                print("   - UI Automator service not running")
                print("   - Accessibility permissions not granted")
                print("   - Device/emulator compatibility issue")
        else:
            print(f"❌ Device Screen API error: {response.status_code}")
    except Exception as e:
        print(f"❌ Device Screen API connection failed: {e}")
    
    # Check device hardware bridge
    try:
        response = requests.get("http://localhost:9999/health", timeout=5)
        if response.status_code == 200:
            print("✅ Device Hardware Bridge responding")
        else:
            print(f"❌ Device Hardware Bridge error: {response.status_code}")
    except Exception as e:
        print(f"❌ Device Hardware Bridge connection failed: {e}")
    
    # Check ADB connection
    try:
        result = subprocess.run(['adb', 'devices'], 
                              capture_output=True, text=True, timeout=5)
        print(f"✅ ADB devices output:")
        print(f"   {result.stdout.strip()}")
        
        # Check if UI automator is running
        result = subprocess.run(['adb', 'shell', 'dumpsys', 'uiautomator'], 
                              capture_output=True, text=True, timeout=10)
        if 'UiAutomationService' in result.stdout:
            print("✅ UI Automator service detected")
        else:
            print("❌ UI Automator service may not be running")
            print("   Try: adb shell settings put secure enabled_accessibility_services com.android.server.uiautomator/.UiAutomatorService")
            
    except Exception as e:
        print(f"❌ ADB check failed: {e}")
    
    print("\n=== RECOMMENDATIONS ===")
    print("1. If UI elements are empty, try restarting maestro:")
    print("   maestro test --help")
    print("2. Check emulator accessibility settings")
    print("3. Try running: adb shell dumpsys uiautomator")
    print("4. Restart the emulator if needed")

if __name__ == "__main__":
    check_maestro_status()