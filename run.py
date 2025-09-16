#!/usr/bin/env python3
"""
Shipsy Address Intelligence - SA-LogiCheck Runner
Starts both Flask backend and React frontend
"""

import subprocess
import sys
import os
import time
import signal
import threading
from pathlib import Path

class AppRunner:
    def __init__(self):
        self.backend_process = None
        self.frontend_process = None
        self.base_dir = Path(__file__).parent.resolve()
        
    def print_header(self):
        print("=" * 60)
        print("🚀 Shipsy Address Intelligence - SA-LogiCheck")
        print("=" * 60)
        
    def setup_backend_venv(self):
        """Setup Python virtual environment for backend"""
        backend_dir = self.base_dir / "backend"
        venv_dir = backend_dir / "venv"
        
        if not venv_dir.exists():
            print("📦 Creating virtual environment for backend...")
            subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], 
                         cwd=str(backend_dir), check=True)
        
        # Get pip path based on OS
        if os.name == 'nt':  # Windows
            pip_path = venv_dir / "Scripts" / "pip"
            python_path = venv_dir / "Scripts" / "python"
        else:  # Unix/Linux/Mac
            pip_path = venv_dir / "bin" / "pip"
            python_path = venv_dir / "bin" / "python"
        
        # Install requirements
        print("📦 Installing backend dependencies...")
        subprocess.run([str(pip_path), "install", "-q", "-r", "requirements.txt"], 
                      cwd=str(backend_dir), check=True)
        
        return str(python_path)
        
    def start_backend(self):
        """Start Flask backend server"""
        try:
            print("\n🔧 Starting Flask backend...")
            backend_dir = self.base_dir / "backend"
            
            # Setup venv and get python path
            python_path = self.setup_backend_venv()
            
            # Start Flask app
            self.backend_process = subprocess.Popen(
                [python_path, "app.py"],
                cwd=str(backend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for backend to start
            time.sleep(2)
            
            if self.backend_process.poll() is None:
                print("✅ Backend running at http://localhost:5000")
                return True
            else:
                print("❌ Failed to start backend")
                return False
                
        except Exception as e:
            print(f"❌ Backend error: {e}")
            return False
    
    def start_frontend(self):
        """Start React frontend server"""
        try:
            print("\n📦 Starting React frontend...")
            frontend_dir = self.base_dir / "frontend"
            
            # Check if node_modules exists
            node_modules = frontend_dir / "node_modules"
            if not node_modules.exists():
                print("📦 Installing frontend dependencies (this may take a minute)...")
                subprocess.run(["npm", "install"], 
                             cwd=str(frontend_dir), 
                             check=True,
                             stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL)
            
            # Start React app
            env = os.environ.copy()
            env["BROWSER"] = "none"  # Prevent auto-opening browser
            
            self.frontend_process = subprocess.Popen(
                ["npm", "start"],
                cwd=str(frontend_dir),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=env
            )
            
            print("✅ Frontend starting at http://localhost:3000")
            print("   (The app will open in your browser automatically)")
            return True
            
        except Exception as e:
            print(f"❌ Frontend error: {e}")
            return False
    
    def monitor_output(self, process, name):
        """Monitor and print process output"""
        try:
            for line in process.stdout:
                if line.strip():
                    print(f"[{name}] {line.strip()}")
        except:
            pass
    
    def run(self):
        """Main run method"""
        self.print_header()
        
        # Start backend
        if not self.start_backend():
            print("\n❌ Failed to start backend. Exiting...")
            return
        
        # Start frontend
        if not self.start_frontend():
            print("\n❌ Failed to start frontend. Exiting...")
            self.shutdown()
            return
        
        print("\n" + "=" * 60)
        print("✨ Shipsy Address Intelligence is running!")
        print("📍 Frontend: http://localhost:3000")
        print("🔧 Backend API: http://localhost:5000/api")
        print("\n🛑 Press Ctrl+C to stop all services")
        print("=" * 60 + "\n")
        
        # Start monitoring threads
        backend_thread = threading.Thread(
            target=self.monitor_output, 
            args=(self.backend_process, "Backend"),
            daemon=True
        )
        backend_thread.start()
        
        frontend_thread = threading.Thread(
            target=self.monitor_output,
            args=(self.frontend_process, "Frontend"),
            daemon=True
        )
        frontend_thread.start()
        
        try:
            # Keep running until interrupted
            while True:
                time.sleep(1)
                
                # Check if processes are still running
                if self.backend_process and self.backend_process.poll() is not None:
                    print("\n⚠️  Backend stopped unexpectedly!")
                    break
                    
                if self.frontend_process and self.frontend_process.poll() is not None:
                    print("\n⚠️  Frontend stopped unexpectedly!")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n🛑 Shutting down services...")
            self.shutdown()
    
    def shutdown(self):
        """Shutdown all services"""
        if self.backend_process:
            try:
                self.backend_process.terminate()
                self.backend_process.wait(timeout=5)
                print("✅ Backend stopped")
            except:
                self.backend_process.kill()
        
        if self.frontend_process:
            try:
                self.frontend_process.terminate()
                self.frontend_process.wait(timeout=5)
                print("✅ Frontend stopped")
            except:
                self.frontend_process.kill()
        
        print("\n👋 Shipsy Address Intelligence stopped successfully")

def check_requirements():
    """Check if required tools are installed"""
    requirements = {
        "Python": sys.version,
        "Node.js": None,
        "npm": None
    }
    
    # Check Node.js
    try:
        result = subprocess.run(["node", "--version"], 
                              capture_output=True, text=True)
        requirements["Node.js"] = result.stdout.strip()
    except:
        print("❌ Node.js is not installed. Please install Node.js 14+ from https://nodejs.org/")
        return False
    
    # Check npm
    try:
        result = subprocess.run(["npm", "--version"], 
                              capture_output=True, text=True)
        requirements["npm"] = result.stdout.strip()
    except:
        print("❌ npm is not installed. Please install Node.js which includes npm")
        return False
    
    print("✅ System Requirements:")
    for tool, version in requirements.items():
        print(f"   • {tool}: {version}")
    print()
    
    return True

if __name__ == "__main__":
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Run the application
    runner = AppRunner()
    try:
        runner.run()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        runner.shutdown()
        sys.exit(1)