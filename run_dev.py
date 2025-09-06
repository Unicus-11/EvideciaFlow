#!/usr/bin/env python3
"""
Development server startup script for EvideciaFlow
Starts both Flask backend and Next.js frontend
"""

import subprocess
import sys
import time
import os
import signal
import threading
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    # Check Python dependencies
    try:
        import flask
        import flask_cors
        import groq
        print("✅ Python dependencies OK")
    except ImportError as e:
        print(f"❌ Missing Python dependency: {e}")
        print("Run: pip install -r requirements.txt")
        return False
    
    # Check Node.js dependencies
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("❌ Frontend directory not found")
        return False
    
    node_modules = frontend_path / "node_modules"
    if not node_modules.exists():
        print("❌ Node modules not installed")
        print("Run: cd frontend && npm install")
        return False
    
    print("✅ Node.js dependencies OK")
    return True

def start_backend():
    """Start Flask backend server"""
    print("🚀 Starting Flask backend on port 5000...")
    try:
        process = subprocess.Popen([
            sys.executable, "app.py"
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process
    except Exception as e:
        print(f"❌ Failed to start backend: {e}")
        return None

def start_frontend():
    """Start Next.js frontend server"""
    print("🚀 Starting Next.js frontend on port 3000...")
    try:
        process = subprocess.Popen([
            "npm", "run", "dev"
        ], cwd="frontend", stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return process
    except Exception as e:
        print(f"❌ Failed to start frontend: {e}")
        return None

def monitor_process(process, name):
    """Monitor a process and print its output"""
    while process.poll() is None:
        output = process.stdout.readline()
        if output:
            print(f"[{name}] {output.strip()}")
        time.sleep(0.1)

def main():
    """Main function"""
    print("=" * 60)
    print("EvideciaFlow Development Server")
    print("=" * 60)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        sys.exit(1)
    
    # Wait a moment for backend to start
    time.sleep(3)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        backend_process.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Both servers are running!")
    print("Backend: http://localhost:5000")
    print("Frontend: http://localhost:3000")
    print("Press Ctrl+C to stop both servers")
    print("=" * 60 + "\n")
    
    # Monitor processes
    try:
        backend_thread = threading.Thread(target=monitor_process, args=(backend_process, "BACKEND"))
        frontend_thread = threading.Thread(target=monitor_process, args=(frontend_process, "FRONTEND"))
        
        backend_thread.daemon = True
        frontend_thread.daemon = True
        
        backend_thread.start()
        frontend_thread.start()
        
        # Wait for processes
        while backend_process.poll() is None and frontend_process.poll() is None:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\n🛑 Shutting down servers...")
        backend_process.terminate()
        frontend_process.terminate()
        print("✅ Servers stopped")

if __name__ == "__main__":
    main()
