#!/usr/bin/env python3
"""
Paper Analyzer Test Script
Tests the paper_analyzer.py module independently or via Flask API
"""

import os
import sys
import json
import requests
from pathlib import Path
from io import StringIO

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_paper_analyzer_direct():
    """Test the paper analyzer module directly"""
    print("=" * 60)
    print("TESTING PAPER ANALYZER DIRECTLY")
    print("=" * 60)
    
    try:
        # Try to import the paper analyzer
        from backend.paper_analyzer import PaperAnalyzer
        print("✓ Successfully imported PaperAnalyzer")
        
        # Try to initialize it
        try:
            # Try with AI manager
            try:
                from ai.ai_manager import AIManager
                ai_manager = AIManager()
                analyzer = PaperAnalyzer(ai_manager=ai_manager)
                print("✓ Initialized PaperAnalyzer with AI Manager")
            except:
                # Fallback without AI manager
                analyzer = PaperAnalyzer()
                print("✓ Initialized PaperAnalyzer without AI Manager")
                
        except Exception as e:
            print(f"✗ Failed to initialize PaperAnalyzer: {e}")
            return False
        
        # Test basic attributes and methods
        print("\n--- Testing Basic Attributes ---")
        attrs_to_check = [
            'available_tools',
            'analysis_storage',
            'ai_manager'
        ]
        
        for attr in attrs_to_check:
            if hasattr(analyzer, attr):
                value = getattr(analyzer, attr)
                print(f"✓ {attr}: {type(value).__name__}")
                if attr == 'available_tools' and isinstance(value, dict):
                    print(f"  Available tools: {list(value.keys())}")
            else:
                print(f"✗ Missing attribute: {attr}")
        
        # Test methods
        print("\n--- Testing Methods ---")
        methods_to_check = [
            'analyze_paper',
            'run_analysis_tool',
            '_get_analysis_data',
            '_save_analysis_data'
        ]
        
        for method in methods_to_check:
            if hasattr(analyzer, method) and callable(getattr(analyzer, method)):
                print(f"✓ Method exists: {method}")
            else:
                print(f"✗ Missing method: {method}")
        
        # Test with sample text
        print("\n--- Testing with Sample Content ---")
        sample_text = """
        This is a sample research paper for testing the Paper Analyzer tools.
        
        Introduction:
        Machine learning has revolutionized many fields of science. However, some studies claim 
        that traditional methods are still superior in certain cases. This contradiction needs
        to be addressed in our methodology.
        
        Methodology:
        We used Protocol A for data collection, following standard procedures outlined in 
        Smith et al. (2020). Our figures show significant improvements over baseline methods.
        
        Results:
        Figure 1 demonstrates the performance gains. Citations to relevant work include
        Jones (2019) and Brown et al. (2021).
        """
        
        try:
            # Create a mock file object
            class MockFile:
                def __init__(self, content):
                    self.content = content
                    self.filename = "test_paper.txt"
                
                def read(self):
                    return self.content.encode()
                
                def stream(self):
                    return StringIO(self.content)
            
            mock_file = MockFile(sample_text)
            
            # Test analyze_paper method
            if hasattr(analyzer, 'analyze_paper'):
                result = analyzer.analyze_paper(mock_file, user_id="test_user")
                print(f"✓ analyze_paper returned: {type(result)}")
                if isinstance(result, dict):
                    print(f"  Success: {result.get('success')}")
                    if 'data' in result:
                        print(f"  Analysis ID: {result['data'].get('analysis_id', 'N/A')}")
            else:
                print("✗ analyze_paper method not found")
                
        except Exception as e:
            print(f"✗ Error testing with sample content: {e}")
        
        return True
        
    except ImportError as e:
        print(f"✗ Failed to import PaperAnalyzer: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False

def test_paper_analyzer_via_api():
    """Test the paper analyzer via Flask API"""
    print("\n" + "=" * 60)
    print("TESTING PAPER ANALYZER VIA API")
    print("=" * 60)
    
    base_url = "http://localhost:5000"
    
    # Test health endpoint
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print("✓ API is running")
            print(f"  Paper Analyzer status: {health_data.get('features', {}).get('paper_analyzer', 'Unknown')}")
        else:
            print(f"✗ Health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"✗ Cannot connect to API: {e}")
        print("  Make sure Flask server is running on localhost:5000")
        return False
    
    # Test the special test endpoint
    try:
        response = requests.get(f"{base_url}/api/test-paper-analyzer", timeout=10)
        if response.status_code == 200:
            print("✓ Test endpoint accessible")
        else:
            print(f"✗ Test endpoint failed: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"✗ Test endpoint error: {e}")
    
    # Test paper analysis with sample text
    print("\n--- Testing Paper Analysis API ---")
    try:
        test_data = {
            'test_text': """
            This is a test research paper for API testing.
            We are evaluating the performance of our paper analyzer system.
            The methodology involves automated text processing and analysis.
            Results indicate successful integration with the Flask API.
            """,
            'test_mode': 'full'
        }
        
        response = requests.post(f"{base_url}/api/test-paper-analyzer", data=test_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✓ API test successful")
            print(f"  Test mode: {result.get('test_mode')}")
            print(f"  Component status: {result.get('results', {}).get('component_status', 'N/A')}")
            
            if 'available_methods' in result.get('results', {}):
                methods = result['results']['available_methods']
                print(f"  Available methods: {len(methods)} found")
                
            if 'analysis_test' in result.get('results', {}):
                analysis_test = result['results']['analysis_test']
                print(f"  Analysis test: {analysis_test.get('success', 'N/A')}")
                
        else:
            print(f"✗ API test failed: {response.status_code}")
            print(f"  Response: {response.text[:200]}...")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ API test error: {e}")
    
    return True

def create_test_files():
    """Create sample test files for testing"""
    print("\n--- Creating Test Files ---")
    
    test_dir = Path("test_files")
    test_dir.mkdir(exist_ok=True)
    
    # Create a sample text file
    sample_text_file = test_dir / "sample_paper.txt"
    with open(sample_text_file, 'w') as f:
        f.write("""
        Sample Research Paper

        Abstract:
        This paper presents a comprehensive analysis of machine learning techniques
        applied to data processing. We demonstrate significant improvements in
        accuracy and efficiency compared to traditional methods.

        Introduction:
        Machine learning has emerged as a powerful tool for data analysis...

        Methodology:
        We employed a combination of supervised and unsupervised learning
        algorithms to process large datasets...

        Results:
        Our experiments show a 25% improvement in processing speed and
        15% increase in accuracy...

        Conclusion:
        The proposed methodology offers substantial benefits for data
        processing applications...
        """)
    
    print(f"✓ Created test file: {sample_text_file}")
    
    # Create a requirements test file
    requirements_file = test_dir / "test_requirements.txt"
    with open(requirements_file, 'w') as f:
        f.write("""
        # Paper Analyzer Test Requirements
        
        Expected functionality:
        1. File upload and processing
        2. Text extraction from various formats
        3. Analysis tool execution
        4. Results generation and download
        5. Status tracking
        
        Test scenarios:
        - Upload text file
        - Upload PDF (if available)
        - Run individual analysis tools
        - Check analysis status
        - Download results
        """)
    
    print(f"✓ Created requirements file: {requirements_file}")
    return test_dir

def run_comprehensive_test():
    """Run all tests"""
    print("🧪 COMPREHENSIVE PAPER ANALYZER TEST")
    print("=" * 80)
    
    success_count = 0
    total_tests = 3
    
    # Test 1: Direct module testing
    if test_paper_analyzer_direct():
        success_count += 1
    
    # Test 2: API testing
    if test_paper_analyzer_via_api():
        success_count += 1
    
    # Test 3: Create test files
    try:
        create_test_files()
        success_count += 1
        print("✓ Test files created successfully")
    except Exception as e:
        print(f"✗ Failed to create test files: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Tests passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("🎉 All tests passed!")
    elif success_count > 0:
        print("⚠️  Some tests passed - check details above")
    else:
        print("❌ All tests failed - check your setup")
    
    print("\n📝 Next steps:")
    if success_count < total_tests:
        print("1. Check that all required modules are installed")
        print("2. Ensure Flask server is running for API tests")
        print("3. Verify paper_analyzer.py exists and is properly implemented")
    
    print("4. Visit http://localhost:5000/api/test-paper-analyzer for web interface")
    print("5. Check the test_files/ directory for sample files")
    print("6. Review the cleaned Flask app for improved structure")

if __name__ == "__main__":
    run_comprehensive_test()