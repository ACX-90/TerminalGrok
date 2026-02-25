
"""
Global Configuration Module for TerminalGrok Project
This module, global_cfg.py, serves as the central hub for defining all global
configurations, paths, and file locations used throughout the TerminalGrok project.
It establishes the foundational settings that govern the behavior of the application,
including debug modes, environment variables, and directory structures.
Key Features:
- Defines global switches for debugging, JSON output, file I/O usage, and user confirmation.
- Retrieves or sets default values for username, operating system type, and workspace path
    based on environment variables or debug mode.
- Constructs essential directory paths such as sandbox, tasks, logs, debug, and file communication.
- Specifies file paths for debug logging, inter-process communication (e.g., grok_fcomm_in, grok_fcomm_out),
    and status markers for communication protocols.
- Ensures the creation of necessary directories if they do not exist, promoting a robust setup.
Important Notes:
- This module is the very basic foundation of the project, ensuring consistency and avoiding
    path definitions in other Python files to prevent conflicts and maintain modularity.
- Environment variables (USERNAME, run_environment, workspace) should be set via start.bat or start.sh
    for production use, or defaults are applied in debug mode.
- Paths are constructed using OS-specific separators (e.g., backslashes for Windows) to ensure portability.
Usage:
- Import this module at the beginning of other scripts to access global configurations.
- Modify switches here to alter application behavior without changing core logic elsewhere.
Author: [ACX-90]
Version: 1.0
Date: [2026/02/20]
"""
import os
import sys
import platform

# Global configuration variables
global_debug = 1
# debug mode switch, set to 1 to print debug info
debug = 1
# debug json switch, if set to 1, the raw json messages sent to and received from grok will be printed
# in terminal for debugging,
debug_json = 1     
# grok_use_fileio switch, if set to 1, the agent will get user input from file,
# and print output to file, which can be used for remote terminal display
grok_use_fileio = 0  
# confirm_need switch, if set to 1, the agent will ask for user confirm before executing tool command
confirm_need = 0

# --- Global configuration from OS ---
# Notice: these environment variables should be set in the OS before running the program
# by launching the program by start.bat or start.sh which sets the environment variables, 
# or by setting the environment variables in the terminal before launching the program

# openrouter: use openai format
# xai: use xai format
# others: not supported yet
ai_vendor = 'xai'
# ai_vendor = 'openrouter'

username = os.getenv('USERNAME')
if not username:
    os.environ['USERNAME'] = "TestUser"
    username = "TestUser"

os_type = sys.platform.lower()

path_sep = "\\" if os_type.startswith("win") else "/"

workspace = os.getenv('workspace')
if not workspace:
    os.environ['workspace'] = "E:\\_Workspace\\GitHub\\TerminalGrok"
    workspace = os.environ['workspace']
    
# --- Directories ---
sandbox = f"{workspace}{path_sep}sandbox"
taskdir = f"{workspace}{path_sep}tasks"
logdir = f"{workspace}{path_sep}logs"
debug_dir = f"{workspace}{path_sep}debug"
fcomm_dir = f"{workspace}{path_sep}fcomm"
token_dir = f"{workspace}{path_sep}tokens"
config_dir = f"{workspace}{path_sep}config"

# --- Files ---
debug_file = f"{debug_dir}{path_sep}grok.json"
mem_file = f"{workspace}{path_sep}memories.txt"
# the file path for agent and remote terminal communication when grok_use_fileio switch is on
# when user use terminal or telegram input, the agent will change reply file to grok_fcomm_out,
# when the agent execute task and want to send the result back to grok, it will change reply file
# to grok_fcomm_out_task, so that the main loop can distinguish the source of the input and handle
# the reply accordingly, for example, when the input is from task execution, the main loop can
# choose to print the reply in terminal instead of sending it back to grok, or do some other 
# special handling for task execution reply
# 0 is for normal conversation input,
# 1 is for telegram bot input,
grok_fcomm_in_src = 0
# terminal or local input
grok_fcomm_in = f"{fcomm_dir}{path_sep}msg.grok"
# daemon task input
grok_fcomm_in_task = f"{fcomm_dir}{path_sep}msg_task.grok"
# telegram or other remote input
grok_fcomm_in_tele = f"{fcomm_dir}{path_sep}msg_tele.grok"
grok_fcomm_in_table = [
    grok_fcomm_in,
    grok_fcomm_in_task,
    grok_fcomm_in_tele,
]

def grok_fcomm_remote():
    return 1 if grok_fcomm_in_src == 1 else 0

# the file path for agent to output tool command and thought when grok_use_fileio switch is on
grok_fcomm_out = f"{fcomm_dir}{path_sep}reply.grok"
grok_fcomm_out_tele = f"{fcomm_dir}{path_sep}reply_tele.grok"
grok_fcomm_out_tele_active = f"{fcomm_dir}{path_sep}send_tele.grok"
grok_fcomm_out_table = [
    grok_fcomm_out,
    grok_fcomm_out_tele,
]

grok_token_file = f"{token_dir}{path_sep}grok.token"
xai_token_file = f"{token_dir}{path_sep}xai.token"
# --- Communication Protocol Markers ---
grok_fcomm_done = "<GROK status=done/>"
grok_fcomm_end = "<GROK status=end/>"

grok_fcomm_start = "<GROK status=start/>"
grok_tool_req_flag = "<tools_req/>"

# --- Ensure necessary directories exist ---
if not os.path.exists(sandbox):
    os.makedirs(sandbox)
if not os.path.exists(taskdir):
    os.makedirs(taskdir)
if not os.path.exists(logdir):
    os.makedirs(logdir)
if not os.path.exists(debug_dir):
    os.makedirs(debug_dir)
if not os.path.exists(fcomm_dir):
    os.makedirs(fcomm_dir)
if not os.path.exists(token_dir):
    os.makedirs(token_dir)

# --- Clear FComm files at startup ---
for fcomm_file in grok_fcomm_in_table:
    if os.path.exists(fcomm_file):
        with open(fcomm_file, "w") as f:
            f.write("")
for fcomm_file in grok_fcomm_out_table:
    if os.path.exists(fcomm_file):
        with open(fcomm_file, "w") as f:
            f.write("")

# --- Load API token ---
with open(grok_token_file, "r") as f:
    grok_token = f.read().rstrip(' \n')
    if grok_token.startswith("#error"):
        print("Error: your Grok API key is invalid.")
        exit(-1)

# --- Load previous memories ---
try:
    with open(mem_file, "r", encoding="utf-8") as f:
        memories = f.read()
except FileNotFoundError:
    memories = "No previous conversation."
