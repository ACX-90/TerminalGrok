import os
import sys

os_type = os.getenv('run_enviroment')
workspace = os.getenv('workspace')
sandbox = f"{workspace}/sandbox"
username = os.getenv('USERNAME')

# get API Key
with open(f"{workspace}/grok.token", "r") as f:
    api_key = f.read().rstrip(' \n')
    if api_key.startswith("#error"):
        print("Error: you API is invalid")
        exit(-1)

# read previous memories
mem_file = f"{workspace}/memories.txt"
try:
    with open(mem_file, "r", encoding="utf-8") as f:
        memories = f.read()
except FileNotFoundError:
    memories = "No previous conversation"
    
msg_system = {
        "role": "system",
        "content": f"<role>You are Grok, an assistant live in {os_type} terminal.</role>\n"
                   "<style>**Your reply MUST use only ASCII, no emoji**, be short and precise, humor.</style>\n"
                   f"<workspace>**Your workspace is {sandbox}, you must only operate file inside and in it's sub directories**</workspace>\n"
                   "<help>You can use batch tools to help the user when necessary.\n"
                   "**you must not do more than 2 things in one batch command, try step by step**\n"
                   "when returncode is 0 you can continue.\n"
                   "when returncode is not 0 you must analyze reason and decide what to do next\n"
                   "when user reject this tool call you must find a correct way to use tools</help>\n"
    }

# print(msg_system)
# exit(-1)

msg_mems = {
        "role": "assistant",
        "content": f"<memory>{memories}</memory>"
    }

msg_hello = {
        "role": "system",
        "content": f"<action>Now say greetings to the user {username}.</action>"
    }

tool_bat = {
        "type": "function",
        "function": {
            "name": "batch",
            "description": f"""Execute Windows Batch commands in the user's terminal. 
                            CRITICAL: Generate commands with RAW Windows Batch syntax:
                            - Use < > not &lt; &gt;
                            - Use && not &amp; &amp;
                            - Use | not &pipe;
                            - Use " not &quot; 
                            - **NEVER use cd, Use only absolute path starts with {sandbox}**
                            - **NEVER use && and other command after EOF**
                            NEVER HTML-encode the command string. Output raw Windows Batch syntax only.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "think": {
                        "type": "string",
                        "description": "You must think carefully what's the best Windows Batch command to do,"
                                       "**you must do it step by step**, check previous result every step,"
                                       "**you must not output dangerous Windows Batch command**, write your thoughts",
                    },
                    "command": {
                        "type": "string",
                        "description": "Raw Windows Batch command with proper Windows Batch syntax (no HTML encoding)"
                    }
                },
                "required": ["think", "command"]
            }
        }
    }

tool_bash = {
        "type": "function",
        "function": {
            "name": "batch",
            "description": f"""Execute bash commands in the user's terminal. 
                            CRITICAL: Generate commands with RAW shell syntax:
                            - Use < > not &lt; &gt;
                            - Use && not &amp; &amp;
                            - Use | not &pipe;
                            - Use " not &quot; 
                            - **NEVER use cd, Use only absolute path starts with {sandbox}**
                            - **NEVER use && and other command after EOF**
                            NEVER HTML-encode the command string. Output raw bash syntax only.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "think": {
                        "type": "string",
                        "description": "You must think carefully what's the best bash command to do,"
                                       "**you must do it step by step**, check previous result every step,"
                                       "**you must not output dangerous bash command**, write your thoughts",
                    },
                    "command": {
                        "type": "string",
                        "description": "Raw bash command with proper shell syntax (no HTML encoding)"
                    }
                },
                "required": ["think", "command"]
            }
        }
    }

tool_batch = tool_bat if sys.platform.lower().__contains__("win") else tool_bash
