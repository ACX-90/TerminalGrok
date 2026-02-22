"""
Main module for the TerminalGrok application.

This script serves as the entry point for the TerminalGrok system, which integrates a Grok AI
agent for conversational interactions via a terminal interface. It begins by importing necessary
modules: global_cfg for configuration, general for shared utilities, agent for AI interactions,
and daemon for background processes.

The script first launches a daemon process using daemon.run_daemon(), which likely handles
persistent tasks or services in the background.

Following daemon initialization, the code enters an infinite loop to manage the conversation
flow with the Grok AI. It handles various states: initial setup where welcome messages are
displayed and default conversation starters are set; scenarios where tools were used in the
previous interaction, allowing the agent to decide on further tool usage; and standard chat
rounds where user input is solicited.

User inputs are processed, with special handling for commands prefixed with '/', which are
treated as controller commands rather than conversational input. These are preprocessed,
and the loop continues if necessary.

The core interaction involves calling agent.grok_chat() to obtain a reply from Grok, which
may include tool calls. If tool calls are present, they are handled via agent.tool_handle(),
setting flags to indicate tool usage. Otherwise, the reply content is processed through
agent.chat_handle().

To manage conversation length and prevent excessive memory usage, the script trims the
message history, retaining the first message and the latest 95, ensuring the total stays
at or below 100 messages. This approach maintains context without unbounded growth.
"""
import copy
import time
import global_cfg as glb
import general as gen
import agent
import daemon
import tool_telecom as telecom
import threading

# ==============================================================
# Daemon
# ==============================================================
daemon.run_daemon()
telecom.start_telegram_bot()

# ==============================================================
# The main loop
# ==============================================================
def main_loop():
    while True:
        if gen.initial == 1:
            gen.debug_out("SYS: First entry, print welcome info and set initial conversation.")
            # first entry print welcome info, and set initial conversation. let grok start the first
            # hello message and self-introduction, then wait for user input
            gen.initial = 0
            agent.print_welcome()
            gen.messages = copy.deepcopy(gen.default_message)
        elif gen.tool_used_last_time:
            gen.debug_out("SYS: Agent used tools last time, let it decide to use tools or not once again.")
            # the agent used tool last time, let it decide to use tools or not once again. if it still
            #  want to use tools, then handle the tool calls directly without asking for user input
            gen.tool_used_last_time = 0
            gen.current_tools = gen.all_avaliable_tools
            gen.debug_out(f"SYS: tools activated")
        else:
            gen.debug_out("SYS: Start a new chat round, ask for user input.")
            # when start a new chat, clear tools option, and ask user input
            # or when the agent decide not to use tools, ask for user input to continue the conversation
            gen.tool_used_last_time = 0
            gen.current_tools = 0
            user_input = agent.get_user_input()
            # when user input starts with "/", it is a command for the python controller,
            # not a normal conversation input, so handle the command first and get the result,
            # then send the result back to grok and get the next reply, until no more command input
            continue_flag = agent.preprocess_user_input(user_input)
            if continue_flag:
                continue
            
        # make conversation with grok and get the reply, 
        # the reply may contain tool calls, if so, handle the tool calls first and get the result,
        # then send the result back to grok and get the next reply,
        # if not, just print the reply content and wait for user input
        reply = agent.grok_chat()
        
        # if the reply contains tool calls, handle them first, 
        # then send the result back to grok and get the next reply,
        # until no more tool calls
        gen.messages.append(reply)
        if reply.tool_calls:
            gen.tool_used_last_time = 1
            agent.tool_handle(reply)
        elif reply.content:
            agent.chat_handle(reply)
        
        # avoid conversation too long
        # can be done better by summarizing the conversation, 
        # but currently just keep the latest 100 messages
        if len(gen.messages) > 100:
            gen.messages = gen.messages[0:1] + gen.messages[-95:]
            gen.save_message = gen.save_message[-95:]
    

main_thread = threading.Thread(target=main_loop, daemon=True)
main_thread.start()

while True:
    time.sleep(1)
    if gen.reset_flag:
        gen.debug_out(f"SYS: Reset flag detected in main thread: {gen.reset_flag}, exiting.")
        break

main_thread.join(timeout=3)
