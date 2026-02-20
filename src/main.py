"""
Main module for the TerminalGrok application.
This script initializes and runs a daemon process, then enters an infinite loop to manage 
conversations with the Grok AI. It handles user inputs, tool calls, and responses, including 
preprocessing commands, managing tool usage flags, and maintaining conversation history 
to prevent excessive length (keeping the latest 100 messages).
"""
from agent import *
from daemon import *

# ==============================================================
# Daemon
# ==============================================================
run_daemon()

# ==============================================================
# The main loop
# ==============================================================
while True:
    if initial == 1:
        debug_out("SYS: First entry, print welcome info and set initial conversation.")
        # first entry print welcome info, and set initial conversation. let grok start the first
        # hello message and self-introduction, then wait for user input
        initial = 0
        print_welcome()
        messages = default_message
    elif tool_used_last_time:
        debug_out("SYS: Agent used tools last time, let it decide to use tools or not once again.")
        # the agent used tool last time, let it decide to use tools or not once again. if it still
        #  want to use tools, then handle the tool calls directly without asking for user input
        tool_used_last_time = 0
        current_tools = tools
    else:
        debug_out("SYS: Start a new chat round, ask for user input.")
        # when start a new chat, clear tools option, and ask user input
        # or when the agent decide not to use tools, ask for user input to continue the conversation
        tool_used_last_time = 0
        current_tools = 0
        user_input = get_user_input()
        # when user input starts with "/", it is a command for the python controller,
        # not a normal conversation input, so handle the command first and get the result,
        # then send the result back to grok and get the next reply, until no more command input
        continue_flag = preprocess_user_input(user_input)
        if continue_flag:
            continue
        
    # make conversation with grok and get the reply, 
    # the reply may contain tool calls, if so, handle the tool calls first and get the result,
    # then send the result back to grok and get the next reply,
    # if not, just print the reply content and wait for user input
    reply = grok_chat()
    
    # if the reply contains tool calls, handle them first, 
    # then send the result back to grok and get the next reply,
    # until no more tool calls
    messages.append(reply)
    if reply.tool_calls:
        tool_used_last_time = 1
        tool_handle(reply)
    elif reply.content:
        chat_handle(reply)
    
    # avoid conversation too long
    # can be done better by summarizing the conversation, 
    # but currently just keep the latest 100 messages
    if len(messages) > 100:
        messages = messages[0:1] + messages[-95:]
        save_message = save_message[-95:]
    



