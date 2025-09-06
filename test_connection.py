#!/usr/bin/env python3
"""
Test script to verify frontend-backend connection
"""

import requests
import json
import time

def test_backend_health():
    """Test if backend is running and healthy"""
    try:
        response = requests.get('http://localhost:5000/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print("✅ Backend is running and healthy")
            print(f"   Status: {data.get('status', 'unknown')}")
            print(f"   Features available: {data.get('features', {})}")
            return True
        else:
            print(f"❌ Backend returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend at http://localhost:5000")
        print("   Make sure Flask server is running: python app.py")
        return False
    except Exception as e:
        print(f"❌ Error testing backend: {e}")
        return False

def test_document_structure_api():
    """Test document structure extraction API"""
    try:
        test_data = {
            "documentText": "Title: Test Paper\n\nAbstract: This is a test abstract.\n\nIntroduction: This is the introduction section."
        }
        
        response = requests.post(
            'http://localhost:5000/api/extract-document-structure',
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            sections = data.get('sections', [])
            print("✅ Document structure API is working")
            print(f"   Extracted {len(sections)} sections")
            if sections:
                print(f"   First section: {sections[0].get('title', 'Unknown')}")
            return True
        else:
            print(f"❌ Document structure API returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing document structure API: {e}")
        return False

def test_section_sequence_api():
    """Test section sequence validation API"""
    try:
        test_data = {
            "sections": ["Title", "Abstract", "Introduction", "Conclusion"]
        }
        
        response = requests.post(
            'http://localhost:5000/api/check-section-sequence',
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            # The response should be a list directly
            if isinstance(data, list):
                print("✅ Section sequence API is working")
                print(f"   Checked {len(data)} sections")
                if data:
                    print(f"   First check: {data[0]}")
                return True
            else:
                print("❌ Section sequence API returned unexpected format")
                print(f"   Response: {data}")
                return False
        else:
            print(f"❌ Section sequence API returned status {response.status_code}")
            print(f"   Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error testing section sequence API: {e}")
        return False

def main():
    print("🔍 Testing EvideciaFlow Backend Connection...")
    print("=" * 50)
    
    # Test backend health
    backend_healthy = test_backend_health()
    print()
    
    if backend_healthy:
        # Test specific APIs
        print("Testing Document Structure API...")
        doc_api_working = test_document_structure_api()
        print()
        
        print("Testing Section Sequence API...")
        seq_api_working = test_section_sequence_api()
        print()
        
        if doc_api_working and seq_api_working:
            print("🎉 All tests passed! Backend is ready for frontend connection.")
        else:
            print("⚠️  Some APIs are not working properly.")
    else:
        print("❌ Backend is not running. Please start it first:")
        print("   python app.py")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
