#!/usr/bin/env python3
"""
Installation script for EvideciaFlow
Installs all required dependencies
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run a command and return success status"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, capture_output=True, text=True)
        print(f"✅ {command}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {command}")
        print(f"Error: {e.stderr}")
        return False

def install_python_deps():
    """Install Python dependencies"""
    print("🐍 Installing Python dependencies...")
    return run_command("pip install -r requirements.txt")

def install_node_deps():
    """Install Node.js dependencies"""
    print("📦 Installing Node.js dependencies...")
    frontend_path = Path("frontend")
    if not frontend_path.exists():
        print("❌ Frontend directory not found")
        return False
    
    return run_command("npm install", cwd="frontend")

def create_directories():
    """Create necessary directories"""
    print("📁 Creating directories...")
    directories = [
        "uploads/temp",
        "uploads/figures",
        "databases",
        "frontend/.next"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created {directory}")
    
    return True

def main():
    """Main installation function"""
    print("=" * 60)
    print("EvideciaFlow Installation Script")
    print("=" * 60)
    
    success = True
    
    # Install Python dependencies
    if not install_python_deps():
        success = False
    
    # Install Node.js dependencies
    if not install_node_deps():
        success = False
    
    # Create directories
    if not create_directories():
        success = False
    
    print("\n" + "=" * 60)
    if success:
        print("🎉 Installation completed successfully!")
        print("\nTo start the development servers:")
        print("  python run_dev.py")
        print("\nOr start them separately:")
        print("  Backend: python app.py")
        print("  Frontend: cd frontend && npm run dev")
    else:
        print("❌ Installation failed. Please check the errors above.")
        sys.exit(1)
    print("=" * 60)

if __name__ == "__main__":
    main()
