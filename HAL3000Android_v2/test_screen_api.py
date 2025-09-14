#!/usr/bin/env python3
"""
Test Device Screen API directly to see if it's getting SSE data
"""

import requests
import time

def test_device_screen_api():
    """Test if the device screen API is working"""
    
    print("=== TESTING DEVICE SCREEN API ===")
    
    # Test the screen-info endpoint multiple times
    for i in range(5):
        try:
            print(f"\nTesting /screen-info (attempt {i+1}/5)...")
            response = requests.get("http://localhost:9998/screen-info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {response.status_code}")
                print(f"✅ Data keys: {list(data.keys())}")
                print(f"✅ Elements count: {len(data.get('elements', []))}")
                print(f"✅ Screen size: {data.get('width')}x{data.get('height')}")
                print(f"✅ Platform: {data.get('platform')}")
                
                if len(data.get('elements', [])) > 0:
                    print(f"🎉 SUCCESS! Found {len(data['elements'])} elements")
                    
                    # Look for Settings
                    elements = data.get('elements', [])
                    settings_elements = [e for e in elements if 'setting' in str(e).lower()]
                    print(f"Settings elements: {len(settings_elements)}")
                    
                    if settings_elements:
                        print(f"Settings element: {settings_elements[0]}")
                    return True
                else:
                    print(f"❌ No elements found in API response")
            else:
                print(f"❌ API error: {response.status_code}")
                print(f"Error text: {response.text}")
                
        except requests.exceptions.Timeout:
            print(f"❌ Timeout on attempt {i+1}")
        except Exception as e:
            print(f"❌ Error on attempt {i+1}: {e}")
        
        if i < 4:  # Don't wait after the last attempt
            print("Waiting 3 seconds before retry...")
            time.sleep(3)
    
    print(f"\n❌ All attempts failed - device screen API not working properly")
    return False

def test_health_endpoint():
    """Test the health endpoint"""
    try:
        response = requests.get("http://localhost:9998/health", timeout=5)
        print(f"Health status: {response.status_code}")
        if response.status_code == 200:
            print("✅ Health check passed")
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Health check error: {e}")

if __name__ == "__main__":
    test_health_endpoint()
    test_device_screen_api()