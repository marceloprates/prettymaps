import subprocess
import sys
import time
import os

def test_tkinter_app_imports():
    """Test that the Tkinter app can be imported without errors"""
    try:
        # Try to import the module
        import importlib.util
        spec = importlib.util.spec_from_file_location("app_tkinter", os.path.abspath("app_tkinter.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        # Check that the main class exists
        assert hasattr(module, "PrettymapsApp"), "PrettymapsApp class not found"
        assert hasattr(module, "main"), "main function not found"
    except Exception as e:
        raise AssertionError(f"Failed to import Tkinter app: {e}")

def test_streamlit_app_runs():
    """Test Streamlit app if streamlit is installed"""
    try:
        import streamlit
    except ImportError:
        # Use pytest to skip if streamlit is not installed
        pytest = sys.modules.get('pytest')
        if pytest:
            pytest.skip("Streamlit not installed")
        return
    
    # Start the Streamlit app in headless mode
    proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", os.path.abspath("app.py"), "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Wait a few seconds to see if it crashes
        time.sleep(10)
        # Check if the process is still running (should be)
        assert proc.poll() is None, "Streamlit app crashed on startup"
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill() 