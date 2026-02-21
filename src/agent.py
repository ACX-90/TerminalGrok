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
- global_cfg: Global configuration module
- tool_fileio: File I/O tool module
- tool_tasks: Task management tool module
Usage:
Run the script to start the agent. Use commands like /r to reset, /q to quit, /m to save memory, etc.
The agent can execute tools based on user input and Grok's responses.
Author: [Your Name or Placeholder]
Date: [Current Date or Placeholder]
"""
import re
import time
import os
import json
import html
import subprocess
import agent_cfg as cfg
import general
import tool_fileio
import tool_tasks
import tool_telecom
import general as gen
import global_cfg as glb

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
        api_key=glb.grok_token,
    )
except Exception as e:
    print(f"OpenAI socks fail {e}")
    exit(-1)

# =======================================================================================
# models and tools config
# =======================================================================================

# tools that the agent can use, 
# currently only batch tool is implemented,
# more tools can be added in the future
tools = [
    cfg.tool_batch,
    cfg.tool_fileio,
    cfg.tool_task,
    cfg.tool_telecom,
]
current_tools = 0

# =======================================================================================
# global controll and status variables
# =======================================================================================

# get_grok_input_from_file:
# get input from fcomm file, with start flag, and clear the file after reading
def get_grok_input_from_file():
    gen.grok_end()
    gen.daemon_pause = 0
    while True:
        # terminal input or local file input received
        if os.path.isfile(glb.grok_fcomm_in):
            with open(glb.grok_fcomm_in, 'r') as f:
                fcomm_rx = f.read()
                if fcomm_rx.find(glb.grok_fcomm_start) >= 0:
                    glb.grok_fcomm_in_src = 0
                    open(glb.grok_fcomm_in, 'w').write('')
                    break
        # daemon task input received
        if os.path.isfile(glb.grok_fcomm_in_task):
            with open(glb.grok_fcomm_in_task, 'r') as f:
                fcomm_rx = f.read()
                if fcomm_rx.find(glb.grok_fcomm_start) >= 0:
                    open(glb.grok_fcomm_in_task, 'w').write('')
                    break
        # telegram or other remote input received
        if os.path.isfile(glb.grok_fcomm_in_tele):
            with open(glb.grok_fcomm_in_tele, 'r') as f:
                fcomm_rx = f.read()
                if fcomm_rx.find(glb.grok_fcomm_start) >= 0:
                    glb.grok_fcomm_in_src = 1
                    open(glb.grok_fcomm_in_tele, 'w').write('')
                    break
        time.sleep(0.1)
    gen.daemon_pause = 1
    return fcomm_rx.replace(glb.grok_fcomm_start, '').strip()

# print_agent_tool:
# print the tool command and grok's thought, and ask for confirm if needed
# use lite formatting for reply in mobile terminal like Telegram
def print_agent_tool(think, command):
    if not glb.grok_fcomm_remote():
        gen.myprint("\n" + "="*60)
        gen.myprint(f"Grok's thought: {think}")
        gen.myprint("-"*60)
        gen.myprint("COMMAND TO EXECUTE:")
        gen.myprint("-"*60)
        gen.myprint(command)
        gen.myprint("="*60)
    else:
        gen.myprint(f"Grok's thought: {think}\n")
        gen.myprint("COMMAND TO EXECUTE:\n")
        gen.myprint(command)
    if glb.confirm_need:
        gen.myprint("Execute? (y/no and reasons): ", end="", flush=True)

# print_welcome:
# print welcome info and instructions for user
def print_welcome():
    gen.myprint(f"/r: Reset session  /q: Quit\n"
             "/m: Save memory    /cm: Clear memory\n"
             "/b: Grok Batch     /c: Need Confirm  /n: No Confirm")

# get_user_input:
# get user input from terminal or file, with grok_use_fileio switch
def get_user_input():
    if glb.grok_use_fileio:
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
    tool_activated = 0
    if format.startswith('/r'):
        gen.initial = 1
        gen.myprint("Reset Session $", end=' ')
        continue_flag = 1
    elif format.startswith('/q'):
        gen.myprint("Quit Session $", end=' ')
        gen.grok_end()
        exit(0)
    elif format.startswith('/m'):
        with open(glb.mem_file, 'a', encoding="utf-8") as f:
            f.write("".join(gen.save_message))
        gen.save_message.clear()
        gen.myprint("Set memories $", end=' ')
        continue_flag = 1
    elif format.startswith('/cm'):
        with open(glb.mem_file, 'w', encoding="utf-8") as f:
            f.write('')
        gen.myprint("Clear Memories $", end=' ')
        continue_flag = 1
    elif format.startswith('/c'):
        glb.confirm_need = 1
        gen.myprint("Confirm Need $", end=' ')
        continue_flag = 1
    elif format.startswith('/n'):
        glb.confirm_need = 0
        gen.myprint("No Confirm $", end=' ')
        continue_flag = 1
    elif format.startswith('/b '):
        # example: $ grok /b get dir of sandbox
        # and grok will try to use batch tool to get the dir of sandbox,
        # and print the command and thought for user confirm
        gen.myprint("Tool Required...", end=' ')
        gen.grok_done()
        gen.tool_used_last_time = 1
        user_input = user_input[3:]
        tool_activated = 1
    # if tool_activated:
    #     user_input += "\nSystem: use tools this round"
    # else:
    #     user_input += f"\nSystem: do not use tools this round, you can require tools next round by {glb.grok_tool_req_flag} **in THE FIRST LINE of your reply** if needed."
    if not continue_flag:
        # save user input to conversation, and save_message for potential saving to mem file
        user_input
        gen.messages.append({"role":"user", "content": user_input})
        gen.save_message.append(f"<user>{user_input}</user>\n")
        gen.debug_json_out({"role":"user", "content": user_input})
    return continue_flag

# get_tool_confirm_info:
# if confirm_need is set, get confirm info from user or file,
# otherwise return default confirm info
def get_tool_confirm_info():
    confirm = "yes, do it now"
    if glb.confirm_need:
        if glb.grok_use_fileio:
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
        tool_choice = "auto" if current_tools else 0
        temperature = 0.0 if current_tools else 0.5
        gen.debug_out(f"Grok is thinking, temperature={temperature}, tool_choice={tool_choice}...")
        completion = client.chat.completions.create(
            model=cfg.model,
            messages=gen.messages,
            tools=current_tools,
            tool_choice=tool_choice,
            temperature=temperature,
        )
        gen.debug_out('Grok made a repy:')
    except Exception as e:
        gen.myprint(e)
        if isinstance(e, AuthenticationError):
            gen.myprint("Error: Invalid API KEY")
            data = "#error: " + glb.grok_token
            with open(glb.grok_token_file, "w") as f:
                f.write(data)
            gen.myprint(f"Please modify {glb.grok_token_file} and reset your API KEY\n")
        exit(-1)
    gen.debug_json_out(completion.dict())
    return completion.choices[0].message

# compress_chat:
# not implemented yet, just a placeholder for future use
def compress_chat():
    return ''

# tool_preprocess:
# preprocess the tool call from grok, print the command and thought, and ask for confirm if needed
# return the confirm info and the command to execute
def tool_preprocess(reply, index=0):
    try:
        tool_call = reply.tool_calls[index]
        tool_name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        agent_think = reply.reasoning
        agent_cmd = args.get("command")
        # DECODE HTML entities if Grok accidentally encodes them in the command, which should be executed
        # as raw syntax
        agent_cmd = html.unescape(agent_cmd)
        # save the tool command and thought to save_message for potential saving to mem file, with some
        #  formatting for future use
        gen.save_message.append(f"<assistant>tool={tool_name}, think={agent_think}, cmd=\n{agent_cmd}\n</assistant>\n")
        print_agent_tool(agent_think, agent_cmd)
        confirm_info = get_tool_confirm_info()
    except Exception as e:
        gen.myprint(f"Error in tool_preprocess: {e}")
        agent_think = reply.reasoning
        agent_cmd = f"ERROR: Failed to parse tool call. Exception: {e}"
        confirm_info = f"no, exception occurred {e}"
    return confirm_info, agent_cmd

# tool_handle_batch:
# handle the batch tool call from grok, currently just print the command and thought, and ask for confirm
def tool_handle_batch(agent_cmd):
    gen.debug_out("Handling batch tool call...")
    try:
        ret = subprocess.run(agent_cmd, text=True, shell=True, capture_output=True)
        gen.tool_result = f"returncode={ret.returncode}, stdout={ret.stdout}, stderr={ret.stderr}"
    except Exception as e:
        gen.tool_result = f"ERROR: Exception occurred while executing batch command. Exception: {e}"

# tool_handle_fileio:
# handle the fileio tool call from grok, currently just print the command and thought, and ask for confirm,
def tool_handle_fileio(agent_cmd):
    gen.debug_out("Handling fileio tool call...")
    try:
        gen.tool_result = tool_fileio.execute_fileio_command(agent_cmd)
    except Exception as e:
        gen.tool_result = f"ERROR: Exception occurred while executing fileio command. Exception: {e}"

# tool_handle_task:
# handle the task tool call from grok, currently just print the command and thought, and ask for confirm,
def tool_handle_task(agent_cmd):
    gen.debug_out("Handling task tool call...")
    try:
        gen.tool_result = tool_tasks.execute_tasks_command(agent_cmd)
    except Exception as e:
        gen.tool_result = f"ERROR: Exception occurred while executing task command. Exception: {e}"

# tool_handler_telecom:
# handle the telecom tool call from grok, currently just print the command and thought, and
def tool_handle_telecom(agent_cmd):
    gen.debug_out("Handling telecom tool call...")
    try:
        gen.tool_result = tool_telecom.execute_telecom_command(agent_cmd)
    except Exception as e:
        gen.tool_result = f"ERROR: Exception occurred while executing telecom command. Exception: {e}"

tool_handler_map = {
    "batch": tool_handle_batch,
    "fileio": tool_handle_fileio,
    "task": tool_handle_task,
    "telecom": tool_handle_telecom,
}

# tool_handle:
# handle the tool calls from grok, currently only print the command and thought, and ask for confirm,
# then execute the command and return the result to grok, more tools can be added in the future
def tool_handle(reply):
    for index, tool_call in enumerate(reply.tool_calls):
        tool_handle = tool_handler_map.get(tool_call.function.name)
        if tool_handle:
            confirm_info, agent_cmd = tool_preprocess(reply, index)
            if confirm_info.startswith("y"):
                tool_handle(agent_cmd)
            else:
                gen.tool_result = f"Tool execution rejected by user, confirm_info: {confirm_info}"
        else:
            gen.tool_result = f"ERROR: no handler for tool {tool_call.function.name}."
        gen.myprint(gen.tool_result)
        gen.save_message.append(f"<tool_result>{gen.tool_result}</tool_result>\n")
        new_message = {"role": "tool", "tool_call_id": tool_call.id, "content": gen.tool_result}
        gen.messages.append(new_message)
        gen.debug_json_out(new_message)
        gen.grok_done()
        
# has_tools_req_tag:
# check if the reply from grok contains the tool request tag, which indicates that grok 
# requires tools for next round
def has_tools_req_tag(text: str) -> bool:
    pattern = r'<tools_req\s*/?>|<tools_req\b[^>]*>.*?</tools_req>'
    return bool(re.search(pattern, text, re.DOTALL | re.IGNORECASE))

# chat handle:
# handle the normal chat reply from grok, save the content to conversation and print it,
# with some formatting for potential future use
def chat_handle(reply):
    gen.save_message.append(f"<assistant>{reply.content}</assistant>\n")
    print_content = reply.content.rstrip("\n$")
    if not glb.grok_fcomm_remote():
        gen.myprint(f"{'-'*60}\nGrok: {print_content}", end=f'\n{'-'*60}\n$ ')
    else:
        gen.myprint(f"{print_content}\n$ ")
    gen.grok_done()
    if has_tools_req_tag(print_content):
        gen.debug_out("Grok requires tools for next round, set tool_used_last_time to 1"
                  " to let it decide to use tools or not once again.")
        gen.tool_used_last_time = 1
