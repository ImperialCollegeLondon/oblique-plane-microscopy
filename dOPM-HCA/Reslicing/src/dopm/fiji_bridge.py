# In src/dopm/fiji_bridge.py

import subprocess
import os
import tempfile
import sys

class FijiBridge:
    def __init__(self, fiji_path: str):
        if not os.path.exists(fiji_path):
            raise FileNotFoundError(f"Fiji executable not found at: {fiji_path}")
        self.fiji_path = fiji_path
        # The __init__ only runs once, so we don't need the print statement here anymore.

    def run_macro(self, macro_code: str, headless: bool = True, timeout_seconds: int = 3600):
        temp_macro_file = tempfile.NamedTemporaryFile(mode='w', suffix='.ijm', delete=False)
        temp_macro_path = temp_macro_file.name
        process = None
        
        try:
            temp_macro_file.write(macro_code)
            temp_macro_file.close()

            command = [self.fiji_path]
            if headless:
                command.append('--headless')
            command.extend(['--run', temp_macro_path])
            
            print(" Launching Fiji subprocess...")
            process = subprocess.Popen(command)
            process.wait(timeout=timeout_seconds)
            print(" Fiji subprocess finished waiting.")

        except Exception as e:
            print(f" An error occurred during Fiji execution: {e}")
            raise
        finally:
            # --- AGGRESSIVE CLEANUP ---
            print("--- Starting post-task cleanup ---")
            if process and process.poll() is None:
                print("   - Fiji launcher did not exit cleanly. Forcing termination.")
                process.terminate()
                process.wait()

            if sys.platform == "win32":
                print("   - Attempting to terminate orphaned Java processes on Windows...")
                # Try to kill both potential process names to be safe
                subprocess.run(['taskkill', '/F', '/IM', 'java.exe', '/T'], capture_output=True)
                subprocess.run(['taskkill', '/F', '/IM', 'ImageJ-win64.exe', '/T'], capture_output=True)
                print("   - Cleanup commands executed.")
            
            if os.path.exists(temp_macro_path):
                os.remove(temp_macro_path)
            print("--- Cleanup complete ---")