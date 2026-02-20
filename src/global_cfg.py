
import os

global_debug = 0

# --- Global configuration from OS ---
if not global_debug:
    # Notice: these environment variables should be set in the OS before running the program
    # by launching the program by start.bat or start.sh which sets the environment variables, 
    # or by setting the environment variables in the terminal before launching the program
    username = os.getenv('USERNAME')
    os_type = os.getenv('run_environment')
    workspace = os.getenv('workspace')
else:
    username = "test_user"
    os_type = "windows"
    workspace = "E:/_Workspace/GitHub/TerminalGrok/"

# --- Directories ---
sandbox = f"{workspace}/sandbox"
taskdir = f"{workspace}/tasks"
logdir = f"{workspace}/logs"

# --- Ensure necessary directories exist ---
if not os.path.exists(sandbox):
    os.makedirs(sandbox)
if not os.path.exists(taskdir):
    os.makedirs(taskdir)
if not os.path.exists(logdir):
    os.makedirs(logdir)
