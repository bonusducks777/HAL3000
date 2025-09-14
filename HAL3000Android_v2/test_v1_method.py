#!/usr/bin/env python3
"""
Test ADB UI Hierarchy Extraction like v1
"""

import subprocess
import xml.etree.ElementTree as ET
import re

def test_adb_ui_extraction():
    """Test if we can get UI hierarchy using v1's method"""
    
    print("=== Testing ADB UI Hierarchy Extraction ===")
    
    # Method 1: Try exec-out like v1
    print("\n1. Testing 'adb exec-out uiautomator dump /dev/stdout'...")
    try:
        result = subprocess.run([
            'adb', 'exec-out', 'uiautomator', 'dump', '/dev/stdout'
        ], capture_output=True, text=True, timeout=15)
        
        print(f"Return code: {result.returncode}")
        print(f"Stdout length: {len(result.stdout)} characters")
        print(f"Stderr: {result.stderr}")
        
        if result.returncode == 0 and result.stdout and len(result.stdout) > 100:
            print("✅ SUCCESS! UI hierarchy extracted")
            print(f"First 200 chars: {result.stdout[:200]}...")
            
            # Count elements
            element_count = result.stdout.count('<node ')
            print(f"Found {element_count} UI nodes")
            
            # Look for Settings
            if 'setting' in result.stdout.lower():
                print("✅ Found 'setting' in UI hierarchy")
            
            return result.stdout
        else:
            print("❌ Failed or empty result")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Method 2: Try standard dump
    print("\n2. Testing 'adb shell uiautomator dump'...")
    try:
        dump_result = subprocess.run([
            'adb', 'shell', 'uiautomator', 'dump'
        ], capture_output=True, text=True, timeout=10)
        
        print(f"Dump return code: {dump_result.returncode}")
        print(f"Dump stderr: {dump_result.stderr}")
        
        if dump_result.returncode == 0:
            # Try to read the file
            cat_result = subprocess.run([
                'adb', 'shell', 'cat', '/sdcard/window_dump.xml'
            ], capture_output=True, text=True, timeout=5)
            
            print(f"Cat return code: {cat_result.returncode}")
            if cat_result.returncode == 0 and cat_result.stdout:
                print(f"✅ SUCCESS! UI dump file readable")
                print(f"Content length: {len(cat_result.stdout)} characters")
                element_count = cat_result.stdout.count('<node ')
                print(f"Found {element_count} UI nodes")
                return cat_result.stdout
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Method 3: Check device capabilities
    print("\n3. Checking device capabilities...")
    try:
        # Check if uiautomator is available
        check_result = subprocess.run([
            'adb', 'shell', 'which', 'uiautomator'
        ], capture_output=True, text=True, timeout=5)
        
        print(f"uiautomator path: {check_result.stdout.strip()}")
        
        # Check Android version
        version_result = subprocess.run([
            'adb', 'shell', 'getprop', 'ro.build.version.release'
        ], capture_output=True, text=True, timeout=5)
        
        print(f"Android version: {version_result.stdout.strip()}")
        
        # Check API level
        api_result = subprocess.run([
            'adb', 'shell', 'getprop', 'ro.build.version.sdk'
        ], capture_output=True, text=True, timeout=5)
        
        print(f"API level: {api_result.stdout.strip()}")
        
    except Exception as e:
        print(f"Error checking capabilities: {e}")
    
    print("\n❌ All UI hierarchy extraction methods failed")
    return None

def parse_ui_hierarchy_v1_style(xml_content):
    """Parse UI hierarchy like v1 does"""
    elements = []
    try:
        root = ET.fromstring(xml_content)
        for node in root.iter():
            if node.tag == 'node':
                bounds = node.get('bounds', '')
                resource_id = node.get('resource-id', '')
                text = node.get('text', '')
                content_desc = node.get('content-desc', '')
                class_name = node.get('class', '')
                clickable = node.get('clickable', 'false') == 'true'
                
                element = {
                    'resource-id': resource_id,
                    'text': text,
                    'content-desc': content_desc,
                    'class': class_name,
                    'clickable': clickable,
                    'bounds': bounds
                }
                
                elements.append(element)
                
                # Check for Settings
                if any(term in str(element).lower() for term in ['setting', 'gear']):
                    print(f"🎯 FOUND SETTINGS ELEMENT: {element}")
    
    except Exception as e:
        print(f"Error parsing XML: {e}")
    
    return elements

if __name__ == "__main__":
    xml_content = test_adb_ui_extraction()
    if xml_content:
        print(f"\n=== PARSING UI ELEMENTS ===")
        elements = parse_ui_hierarchy_v1_style(xml_content)
        print(f"Parsed {len(elements)} elements")
        
        # Look for Settings specifically
        settings_elements = [e for e in elements if 'setting' in str(e).lower()]
        print(f"Found {len(settings_elements)} Settings-related elements")
        for elem in settings_elements:
            print(f"Settings element: {elem}")