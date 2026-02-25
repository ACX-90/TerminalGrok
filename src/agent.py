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
import copy
import time
import os
import json
import html
import subprocess
import general as gen
import global_cfg as glb
import tools
import ai

# =======================================================================================
# Initialize global variables and configurations
# =======================================================================================

from openai import (
    OpenAI,
    AuthenticationError,
)

# setup all tools
tools.load_all_tools()
tool_def = ""
tool_brief = ""
tool_list = []
current_tools = []
tool_handler_map = {}
for name, value in tools.tools.items():
    brief = value['prompt']['brief']
    rule = value['prompt']['rule']
    tool_brief += f"<tool name=\"{name}\"><brief>{brief}</brief></tool>\n"
    tool_def += f"<tool name=\"{name}\"><brief>{brief}</brief><rule>{rule}</rule></tool>\n"
    tool_list.append(value['definition'])
    tool_handler_map.update({name: value['handler']})

# setup agent configuration
agent_cfg = gen.get_cfg(f"agent")

system_prompt = agent_cfg["system"]
system_prompt = system_prompt.replace("<OS_TYPE/>", glb.os_type)
system_prompt = system_prompt.replace("<USER_NAME/>", glb.username)
system_prompt = system_prompt.replace("<MEMORY/>", glb.memories)
system_prompt = system_prompt.replace("<SANDBOX_PATH/>", glb.sandbox)
system_prompt = system_prompt.replace("<TOOLS_DEF/>", tool_def)
agent_cfg["system"] = system_prompt
gen.message_init(system_prompt)

tool_router_prompt = agent_cfg["toolRouter"]
tool_router_prompt = tool_router_prompt.replace("<TOOLS_BRIEF/>", f"<tools>{tool_brief}</tools>")
agent_cfg["toolRouter"] = tool_router_prompt

# setup ai
ai.load_all_components()

# =======================================================================================
# functions for agent operation
# =======================================================================================
# __get_grok_input_from_file:
# get input from fcomm file, with start flag, and clear the file after reading
def __get_grok_input_from_file():
    gen.grok_end()
    gen.daemon_pause = 0
    while True:
        for filename in glb.grok_fcomm_in_table:
            if not os.path.isfile(filename):
                continue
            with open(filename, 'r') as f:
                fcomm_rx = f.read()
            # find start flag in the file, if found, clear the file and return 
            # the content after the start flag as user input
            if fcomm_rx.find(glb.grok_fcomm_start) >= 0:
                open(filename, 'w').write('')
                gen.daemon_pause = 1
                if filename == glb.grok_fcomm_in_tele:
                    glb.grok_fcomm_in_src = 1
                elif filename == glb.grok_fcomm_in:
                    glb.grok_fcomm_in_src = 0
                return fcomm_rx.replace(glb.grok_fcomm_start, '').strip()
        time.sleep(0.1)

# __print_agent_tool:
# print the tool command and grok's thought, and ask for confirm if needed
# use lite formatting for reply in mobile terminal like Telegram
def __print_agent_tool(think, command):
    if not glb.grok_fcomm_remote():
        print_content = f"\n{"="*60}\n"
        if think:
            print_content += f"Grok's thought: {think}"\
                        f"{'-'*60}\n"
        print_content += f"COMMAND TO EXECUTE:\n"\
                        f"{'-'*60}\n"\
                        f"{command}\n"\
                        f"{'='*60}"
        gen.myprint(print_content)
    else:
        if len(think) > 300:
            gen.myprint(f"<grok_tele_file name=\"grok_thought.txt\">{think}</grok_tele_file>\n")
        else:
            gen.myprint(f"Grok's thought: {think}\n")
        gen.myprint(f"COMMAND TO EXECUTE:\n{command}")
    if glb.confirm_need:
        gen.myprint("Execute? (y/no and reasons): ", end="", flush=True)

# print_welcome:
# print welcome info and instructions for user
def print_welcome():
    gen.myprint(gen.command_description)

# get_user_input:
# get user input from terminal or file, with grok_use_fileio switch
def get_user_input():
    if glb.grok_use_fileio:
        user_input = __get_grok_input_from_file() 
    else:
        user_input = input()
    print(f"User input: {user_input}")
    return user_input

# tool_router:
# route the tool call to corresponding tool handler based on tool name
def tool_router(user_input):
    if not gen.tool_enable_flag:
        return 0
    global current_tools
    time1 = time.time()
    aux_reply = ai.func(func="chat",
                        mode = 'aux',
                        model=agent_cfg["model"]["aux"],
                        messages=[
                            {"role": "user", "content": agent_cfg["toolRouter"]}, 
                            {"role": "user", "content": user_input}
                        ],
                        temperature=0.2)
    aux_reply = aux_reply["content"]
    time_elapsed = time.time() - time1
    gen.debug_out(f"Tool router auxiliary model latency: {time_elapsed:.2f} seconds")
    gen.debug_out(f"Tool router auxiliary model reply: {aux_reply}")
    if aux_reply.strip().lower().find("yes") >= 0:
        gen.tool_used_last_time = 1
        current_tools = tool_list
    else:
        gen.tool_used_last_time = 0
        current_tools = []
        return 0
    
# preprocess_user_input:
# preprocess user input, return a flag to indicate whether to continue the loop directly
def preprocess_user_input(user_input):
    continue_flag = 0
    format = user_input.lower().strip()
    if format.startswith("/"):
        cmd1 = format[1:2]
        cmd2 = format[1:3]
        if cmd1 in gen.command_handler:
            gen.command_handler[cmd1]()
        elif cmd2 in gen.command_handler:
            gen.command_handler[cmd2]()
        else:
            gen.myprint("Unknown command, please try again.")
        gen.grok_done()
        continue_flag = 1
    else:
        # use another model to judge whether the user wants to use tools.
        tool_router(user_input)
        # save user input to conversation, and save_message for potential saving to mem file
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
            confirm_info = __get_grok_input_from_file() 
        else:
            confirm_info = input()
        if not confirm_info or confirm_info.startswith(" "):
            confirm_info = confirm
        else:
            confirm_info = confirm_info.lower()
    else:
        confirm_info = confirm
    return confirm_info

# compress_chat:
# not implemented yet, just a placeholder for future use
def compress_chat():
    return ''

# tool_preprocess:
# preprocess the tool call from grok, print the command and thought, and ask for confirm if needed
# return the confirm info and the command to execute
def tool_preprocess(reply: dict, index=0):
    try:
        tool_call = reply["tool_calls"][index]
        tool_name = tool_call["function"]["name"]
        args = json.loads(tool_call["function"]["arguments"])
        agent_think = reply["reasoning"]
        agent_cmd = args.get("command")
        # DECODE HTML entities if Grok accidentally encodes them in the command, which should be executed
        # as raw syntax
        agent_cmd = html.unescape(agent_cmd)
        # save the tool command and thought to save_message for potential saving to mem file, with some
        #  formatting for future use
        gen.save_message.append(f"<assistant>tool={tool_name}, think={agent_think}, cmd=\n{agent_cmd}\n</assistant>\n")
        __print_agent_tool(agent_think, agent_cmd)
        confirm_info = get_tool_confirm_info()
    except Exception as e:
        gen.myprint(f"Error in tool_preprocess: {e}")
        agent_think = reply["reasoning"]
        agent_cmd = f"ERROR: Failed to parse tool call. Exception: {e}"
        confirm_info = f"no, exception occurred {e}"
    return confirm_info, agent_cmd

# tool_handle:
# handle the tool calls from grok, currently only print the command and thought, and ask for confirm,
# then execute the command and return the result to grok, more tools can be added in the future
def tool_handle(reply):
    for index, tool_call in enumerate(reply["tool_calls"]):
        tool_handle = tool_handler_map.get(tool_call["function"]["name"])
        if tool_handle:
            confirm_info, agent_cmd = tool_preprocess(reply, index)
            if confirm_info.startswith("y"):
                gen.tool_result = tool_handle(agent_cmd)
            else:
                gen.tool_result = f"Tool execution rejected by user, confirm_info: {confirm_info}"
        else:
            gen.tool_result = f"ERROR: no handler for tool {tool_call['function']['name']}."
        if glb.grok_fcomm_remote() and len(gen.tool_result) > 300:
            gen.myprint(f"<grok_tele_file name=\"grok_tool_result.txt\">{gen.tool_result}</grok_tele_file>\n")
        else:
            gen.myprint(gen.tool_result)
        gen.save_message.append(f"<tool_result>{gen.tool_result}</tool_result>\n")
        new_message = {"role": "tool", "tool_call_id": tool_call["id"], "content": gen.tool_result}
        gen.messages.append(new_message)
        gen.debug_json_out(new_message)
        gen.grok_done()

# chat handle:
# handle the normal chat reply from grok, save the content to conversation and print it,
# with some formatting for potential future use
def chat_handle(reply):
    gen.save_message.append(f"<assistant>{reply["content"]}</assistant>\n")
    print_content = reply["content"].rstrip("\n$")
    if not glb.grok_fcomm_remote():
        gen.myprint(f"{'-'*60}\nGrok: {print_content}", end=f'\n{'-'*60}\n$ ')
    else:
        gen.myprint(f"{print_content}\n$ ")
    gen.grok_done()

# grok_chat:
# make a chat request to grok, with current messages and tools
def grok_chat():
    # try:
    tool_choice = "auto" if current_tools else "none"
    temperature = 0.2 if current_tools else 0.7
    gen.debug_out(f"Grok is thinking, temperature={temperature}, tool_choice={tool_choice}...")
    time1 = time.time()
    main_reply = ai.func(func="chat",
                        mode = 'main',
                        model=agent_cfg["model"]["main"],
                        messages=gen.messages,
                        tools=current_tools,
                        tool_choice=tool_choice,
                        temperature=temperature,)
    time_elapsed = time.time() - time1
    gen.debug_out(f"Grok response latency: {time_elapsed:.2f} seconds")
    gen.debug_out('Grok made a repy:')

    gen.messages.append({
            "role": "assistant", 
            "content": main_reply["content"],
            "tool_calls": main_reply["tool_calls"]
        })
            
    # if the reply contains tool calls, handle them first, then send the result back to 
    # grok and get the next reply, until no more tool calls
    if main_reply["tool_calls"]:
        gen.tool_used_last_time = 1
        tool_handle(main_reply)
    elif main_reply["content"]:
        chat_handle(main_reply)
    return
