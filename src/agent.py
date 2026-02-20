"""
TerminalGrok Agent Module
This module implements an AI agent that interacts with the Grok model via OpenRouter API.
It provides a conversational interface where users can chat with Grok, execute commands using tools,
and manage conversation history. The agent supports features like session reset, memory saving,
tool confirmation, and file-based communication for remote terminals.
Key Features:
- Conversational AI using Grok-4.1-Fast model
- Tool integration for batch commands, file I/O, and task management
- Proxy support for network requests
- Debug and logging capabilities
- File-based I/O for remote terminal communication
- Memory management for conversation history
Dependencies:
- openai: For API interactions
- agent_cfg: Configuration module
- tool_fileio: File I/O tool module
- tool_tasks: Task management tool module
Usage:
Run the script to start the agent. Use commands like /r to reset, /q to quit, /m to save memory, etc.
The agent can execute tools based on user input and Grok's responses.
Author: [Your Name or Placeholder]
Date: [Current Date or Placeholder]
"""
import time
import os
import json
import html
import subprocess
import agent_cfg
import tool_fileio
import tool_tasks
# use clash as system proxy and it's a socks -> socks5 fix for linux
# these environment variables must be set before importing openai client,
# otherwise the proxy setting will not work
os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:7890'
os.environ['all_proxy'] = 'socks5://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
from openai import (
    OpenAI,
    AuthenticationError,
)

# setup openrouter client
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=agent_cfg.grok_token,
    )
except Exception as e:
    print(f"OpenAI socks fail {e}")
    exit(-1)

# =======================================================================================
# models and tools config
# =======================================================================================
# model from openrouter, can be modified to other vendors' models if needed
# compress_model user openrouter's free model, which can be used for compressing
# conversation history to save token, but currently not implemented yet
model = "x-ai/grok-4.1-fast"            # Grok-4.1-Fast from openrouter
compress_model = "openrouter/free"

# default messages for conversation, can be modified by user input commands
# the first 2 messages are system messages, which are necessary for grok to work,
# and should not be removed,
# the 3rd message is a hello message, which can be removed if user want grok to start with no greeting
default_message = [
    agent_cfg.msg_system,       # 0, must be preserved
]
# compress_message is for future use, currently not implemented yet
compress_message = [
    
]
# messages is the current conversation history, which will be sent to grok for each chat request,
messages = default_message
# save_message is the conversation history that will be saved to mem file when user input /m command,
# it's in plain text format for potential future use, currently it's just a copy of messages with
# some formatting, but in the future it can be modified to save more info or in a different format
save_message = []

# tools that the agent can use, 
# currently only batch tool is implemented,
# more tools can be added in the future
tools = [
    agent_cfg.tool_batch,
    agent_cfg.tool_fileio,
    agent_cfg.tool_task,
]
current_tools = 0

# =======================================================================================
# global controll and status variables
# =======================================================================================
# debug mode switch, set to 1 to print debug info
debug = 0
# debug json switch, if set to 1, the raw json messages sent to and received from grok will be printed
# in terminal for debugging,
debug_json = 1              
# initial switch, to print welcome info and set default conversation at the first entry
initial = 1                 
# grok_use_fileio switch, if set to 1, the agent will get user input from file,
# and print output to file, which can be used for remote terminal display
grok_use_fileio = 1               
# confirm_need switch, if set to 1, the agent will ask for user confirm before executing tool command
confirm_need = 1
# a flag to indicate whether the agent used tool last time, 
# if yes, the agent will not ask for user input, but directly decide to use tools or not once again,
# which can be useful when the agent need to use tools for several times in a row
tool_used_last_time = 0
# the file path for agent and remote terminal communication when grok_use_fileio switch is on
grok_fcomm_in = f"{agent_cfg.workspace}/fcomm/msg.grok"
grok_fcomm_in_task = f"{agent_cfg.workspace}/fcomm/msg_task.grok"
# the file path for agent to output tool command and thought when grok_use_fileio switch is on
grok_fcomm_out = f"{agent_cfg.workspace}/fcomm/reply.grok"

# myprint:
# print text in terminal only, or give to another terminal
def myprint_fcomm(*args, **kwargs):
    if grok_use_fileio:
        if not os.path.isdir(f"{agent_cfg.workspace}/fcomm"):
            os.makedirs(f"{agent_cfg.workspace}/fcomm")
        if os.path.isfile(grok_fcomm_out):
            operation = "a"
        else:
            operation = "w"
        with open(grok_fcomm_out, operation) as f:
            print(*args, file=f, **kwargs)

# myprint2:
def myprint(*args, **kwargs):
    myprint_fcomm(*args, **kwargs)
    print(*args, **kwargs)

# debug_out:
# print debug info in terminal if debug mode is on
def debug_out(*args, **kwargs):
    if debug:
        print(*args, **kwargs)

# debug_json_out:
# print json data to file if debug_json switch is on
debug_json_cnt = 0
def debug_json_out(data):
    if debug_json:
        global debug_json_cnt
        debug_dir = f"{agent_cfg.workspace}/debug"
        debug_file = f"{debug_dir}/grok.json"
        if not os.path.isdir(debug_dir):
            os.makedirs(debug_dir)
        if debug_json_cnt == 0:
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write('')
        if not os.path.isfile(debug_file):
            operation = "w"
        else:
            operation = "a"
        with open(debug_file, operation, encoding="utf-8") as f:
            f.write(f"\n\n==== Message {debug_json_cnt} ========================\n\n")
            json.dump(data, f, ensure_ascii=False, indent=4)
        debug_json_cnt += 1

# grok_done:
# output done flag to fcomm file
# the remote terminal can print data
def grok_done():
    myprint_fcomm("\n<GROK status=DONE></GROK>")

# grok_end:
# output end flag to fcomm file
# the remote terminal can stop waiting
def grok_end():
    myprint_fcomm("\n<GROK status=END></GROK>")

# get_grok_input_from_file:
# get input from fcomm file, with start flag, and clear the file after reading
def get_grok_input_from_file():
    grok_end()
    global daemon_pause
    daemon_pause = 0
    grok_start_flag = "<GROK status=start></GROK>"
    while True:
        if os.path.isfile(grok_fcomm_in):
            with open(grok_fcomm_in, 'r') as f:
                fcomm_rx = f.read()
                if fcomm_rx.find(grok_start_flag) >= 0:
                    open(grok_fcomm_in, 'w').write('')
                    break
        if os.path.isfile(grok_fcomm_in_task):
            with open(grok_fcomm_in_task, 'r') as f:
                fcomm_rx = f.read()
                if fcomm_rx.find(grok_start_flag) >= 0:
                    open(grok_fcomm_in_task, 'w').write('')
                    break
        time.sleep(0.1)
    daemon_pause = 1
    return fcomm_rx.replace(grok_start_flag, '').strip()

# print_agent_tool:
# print the tool command and grok's thought, and ask for confirm if needed
def print_agent_tool(think, command):
    myprint("\n" + "="*60)
    myprint(f"Grok's thought: {think}")
    myprint("-"*60)
    myprint("COMMAND TO EXECUTE:")
    myprint("-"*60)
    myprint(command)
    myprint("="*60)
    if confirm_need:
        myprint("Execute? (y/no and reasons): ", end="", flush=True)

# print_welcome:
# print welcome info and instructions for user
def print_welcome():
    myprint(f"/r: Reset session  /q: Quit\n"
             "/m: Save memory    /cm: Clear memory\n"
             "/b: Grok Batch     /c: Need Confirm  /n: No Confirm")

# get_user_input:
# get user input from terminal or file, with grok_use_fileio switch
def get_user_input():
    if grok_use_fileio:
        user_input = get_grok_input_from_file() 
    else:
        user_input = input()
    print(f"User input: {user_input}")
    return user_input

# preprocess_user_input:
# preprocess user input, return a flag to indicate whether to continue the loop directly
def preprocess_user_input(user_input):
    continue_flag = 0
    format = user_input.lower()
    if format.startswith('/r'):
        global initial
        initial = 1
        myprint("Reset Session $", end=' ')
        continue_flag = 1
    elif format.startswith('/q'):
        myprint("Quit Session $", end=' ')
        grok_end()
        exit(0)
    elif format.startswith('/m'):
        with open(agent_cfg.mem_file, 'a', encoding="utf-8") as f:
            f.write("".join(save_message))
        save_message.clear()
        myprint("Set memories $", end=' ')
        continue_flag = 1
    elif format.startswith('/cm'):
        with open(agent_cfg.mem_file, 'w', encoding="utf-8") as f:
            f.write('')
        myprint("Clear Memories $", end=' ')
        continue_flag = 1
    elif format.startswith('/c'):
        global confirm_need
        confirm_need = 1
        myprint("Confirm Need $", end=' ')
        continue_flag = 1
    elif format.startswith('/n'):
        confirm_need = 0
        myprint("No Confirm $", end=' ')
        continue_flag = 1
    elif format.startswith('/b '):
        # example: $ grok /b get dir of sandbox
        # and grok will try to use batch tool to get the dir of sandbox,
        # and print the command and thought for user confirm
        myprint("Tool Required...", end=' ')
        grok_done()
        global current_tools, tool_used_last_time
        current_tools = tools
        tool_used_last_time = 1
        user_input = user_input[3:]
    if not continue_flag:
        # save user input to conversation, and save_message for potential saving to mem file
        messages.append({"role":"user", "content": user_input})
        save_message.append(f"<user>{user_input}</user>\n")
        debug_json_out({"role":"user", "content": user_input})
    return continue_flag

# get_tool_confirm_info:
# if confirm_need is set, get confirm info from user or file,
# otherwise return default confirm info
def get_tool_confirm_info():
    confirm = "yes, do it now"
    if confirm_need:
        if grok_use_fileio:
            confirm_info = get_grok_input_from_file() 
        else:
            confirm_info = input()
        if not confirm_info or confirm_info.startswith(" "):
            confirm_info = confirm
        else:
            confirm_info = confirm_info.lower()
    else:
        confirm_info = confirm
    return confirm_info

# grok_chat:
# make a chat request to grok, with current messages and tools
def grok_chat():
    try:
        debug_out("Grok is thinking...")
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=current_tools,
            tool_choice="auto" if current_tools else 0,
            temperature=0.0 if current_tools else 1.0,
        )
        debug_out('Grok made a repy:')
    except Exception as e:
        myprint(e)
        if isinstance(e, AuthenticationError):
            myprint("Error: Invalid API KEY")
            data = "#error: " + agent_cfg.grok_token
            with open(agent_cfg.grok_token_file, "w") as f:
                f.write(data)
            myprint(f"Please modify {agent_cfg.grok_token_file} and reset your API KEY\n")
        exit(-1)
    debug_json_out(completion.dict())
    return completion.choices[0].message

# compress_chat:
# not implemented yet, just a placeholder for future use
def compress_chat():
    return ''

# tool_preprocess:
# preprocess the tool call from grok, print the command and thought, and ask for confirm if needed
# return the confirm info and the command to execute
def tool_preprocess(reply):
    tool_call = reply.tool_calls[0]
    tool_name = tool_call.function.name
    args = json.loads(tool_call.function.arguments)
    agent_think = reply.reasoning
    agent_cmd = args.get("command")
    # DECODE HTML entities if Grok accidentally encodes them in the command, which should be executed
    # as raw syntax
    agent_cmd = html.unescape(agent_cmd)
    # save the tool command and thought to save_message for potential saving to mem file, with some
    #  formatting for future use
    save_message.append(f"<assistant>tool={tool_name}, think={agent_think}, cmd=\n{agent_cmd}\n</assistant>\n")
    print_agent_tool(agent_think, agent_cmd)
    confirm_info = get_tool_confirm_info()
    return confirm_info, agent_cmd

# tool_handle_batch:
# handle the batch tool call from grok, currently just print the command and thought, and ask for confirm
def tool_handle_batch(reply):
    global tool_result
    confirm_info, agent_cmd = tool_preprocess(reply)
    if confirm_info.startswith('y'):
        ret = subprocess.run(agent_cmd, text=True, shell=True, capture_output=True)
        tool_result = f"returncode={ret.returncode}, stdout={ret.stdout}, stderr={ret.stderr}"
    else:
        tool_result = f"returncode=-1, stderr=user temporarily declined tool call once."

# tool_handle_fileio:
# handle the fileio tool call from grok, currently just print the command and thought, and ask for confirm,
def tool_handle_fileio(reply):
    global tool_result
    confirm_info, agent_cmd = tool_preprocess(reply)
    if confirm_info.startswith('y'):
        try:
            tool_result = tool_fileio.execute_fileio_command(agent_cmd)
        except Exception as e:
            tool_result = f"ERROR: Exception occurred while executing fileio command. Exception: {e}"
    else:
        tool_result = f"returncode=-1, stderr=user temporarily declined tool call once."

# tool_handle_task:
# handle the task tool call from grok, currently just print the command and thought, and ask for confirm,
def tool_handle_task(reply):
    global tool_result
    confirm_info, agent_cmd = tool_preprocess(reply)
    if confirm_info.startswith('y'):
        try:
            tool_result = tool_tasks.execute_tasks_command(agent_cmd)
        except Exception as e:
            tool_result = f"ERROR: Exception occurred while executing task command. Exception: {e}"
    else:
        tool_result = f"returncode=-1, stderr=user temporarily declined tool call once."

# tool_handle:
# handle the tool calls from grok, currently only print the command and thought, and ask for confirm,
# then execute the command and return the result to grok, more tools can be added in the future
def tool_handle(reply):
    global tool_result
    for tool_call in reply.tool_calls:
        match tool_call.function.name:
            case "batch":
                debug_out("Handling batch tool call...")
                tool_handle_batch(reply)
            case "fileio":
                debug_out("Handling fileio tool call...")
                tool_handle_fileio(reply)
            case "task":
                debug_out("Handling task tool call...")
                tool_handle_task(reply)
            case _:
                tool_result = f"ERROR: unknown tool {tool_call.function.name}."
        myprint(tool_result)
        grok_done()
        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
        save_message.append(f"<tool_result>{tool_result}</tool_result>\n")

# chat handle:
# handle the normal chat reply from grok, save the content to conversation and print it,
# with some formatting for potential future use
def chat_handle(reply):
    save_message.append(f"<assistant>{reply.content}</assistant>\n")
    print_content = reply.content.rstrip("\n$")
    myprint(f"{'-'*60}\nGrok: {print_content}", end=f'\n{'-'*60}\n$ ')
    grok_done()
