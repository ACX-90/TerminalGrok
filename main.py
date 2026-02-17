import time
import os
import json
import html
import subprocess
import agent_cfg
# use clash as system proxy and it's a socks -> socks5 fix
os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:7890'
os.environ['all_proxy'] = 'socks5://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
from openai import (
    OpenAI,
    AuthenticationError,
)

# setup openrouter client, or other vendors
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        # base_url="https://api.x.ai/v1",
        api_key=agent_cfg.api_key,
    )
except Exception as e:
    print("OpenAI socks fail")
    print(e)
    exit(-1)

# model and prompts
model = "x-ai/grok-4.1-fast"        # from openrouter
# model = "grok-4-1-fast-reasoning" # from xAI
default_message = [
    agent_cfg.msg_system,       # 0, must be preserved
    agent_cfg.msg_mems,         # 1, must be preserved
    agent_cfg.msg_hello,        # 2, can be dropped
]
tools = [
    agent_cfg.tool_batch,
]

# prepare global variables
debug = 0
grok_file = 1
confirm_need = 1
save_message = []
messages = default_message
initial = 1
tool_active = 0
current_tools = 0
tool_result = ''


def myprint(*args, **kwargs):
    if grok_file:
        with open("reply.grok", "a", encoding="utf-8") as f:
            print(*args, file=f, **kwargs)
    print(*args, **kwargs)

def get_grok_input_from_file():
    grok_done()
    grok_end()
    while True:
        rx = f'{agent_cfg.workspace}/msg.grok'
        if os.path.isfile(rx):
            with open(rx, 'r') as f:
                x = f.read()
                if x.find("<GROK status=start></GROK>") >= 0:
                    x = x.replace("<GROK status=start></GROK>", "")
                    if debug:
                        print(f"inputfile: {x}")
                    open(rx, 'w').write('')
                    break
        time.sleep(1)
    return x

def grok_done():
    myprint("\n<GROK status=DONE></GROK>")

def grok_end():
    with open('end.grok', 'w') as f:
        f.write("end")

def print_agent_tool(think, command):
    myprint("\n" + "="*60)
    myprint(f"Grok's thought: {think}")
    myprint("-"*60)
    myprint("COMMAND TO EXECUTE:")
    myprint("-"*60)
    myprint(command)
    myprint("="*60)
    myprint("Execute? (y/no and reasons): ", end="", flush=True)

def print_welcome():
    myprint(f"/r: Reset session  /q: Quit\n"
             "/m: Save memory    /cm: Clear memory\n"
             "/b: Grok Batch     /c: Need Confirm  /n: No Confirm")

##############################################################
# The main loop
##############################################################
while True:
    # print hint
    if initial == 1:
        initial = 0
        print_welcome()
        messages = default_message
    elif tool_active:
        tool_active = 0
        current_tools = tools
    else:
        current_tools = 0
        tool_active = 0
        if grok_file:
            user_input = get_grok_input_from_file() 
        else:
            user_input = input()

        format = user_input.lower()
        if format.startswith('/r'):
            initial = 1
            myprint("Reset Session $", end=' ')
            continue
        elif format.startswith('/q'):
            myprint("Quit Session $", end=' ')
            grok_done()
            grok_end()
            break
        elif format.startswith('/m'):
            with open(agent_cfg.mem_file, 'a', encoding="utf-8") as f:
                f.write("".join(save_message))
            save_message = []
            myprint("Set memories $", end=' ')
            continue
        elif format.startswith('/cm'):
            with open(agent_cfg.mem_file, 'w', encoding="utf-8") as f:
                f.write('')
            myprint("Clear Memories $", end=' ')
            continue
        elif format.startswith('/c'):
            confirm_need = 1
            myprint("Confirm Need $", end=' ')
            continue
        elif format.startswith('/n'):
            confirm_need = 0
            myprint("No Confirm $", end=' ')
            continue
        if format.startswith('/b '):
            # example: /b output asdwerasdwer to file test.txt
            myprint("Tool Required...", end=' ')
            grok_done()
            current_tools = tools
            tool_active = 1
            user_input = user_input[3:]
        messages.append({"role":"user", "content": user_input})
        save_message.append(f"<user>{user_input}</user>\n")
        
    # make conversation
    try:
        if debug:
            myprint("Grok is thinking...")
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=current_tools,
            tool_choice="auto" if current_tools else 0,
            temperature=0.0 if current_tools else 1.0,
        )
        if debug:
            myprint('Grok made a repy:')
    except Exception as e:
        if isinstance(e, AuthenticationError):
            myprint(e)
            myprint("Error: Invalid API KEY")
            data = "#error: " + agent_cfg.api_key
            with open(f"{agent_cfg.workspace}/grok.token", "w") as f:
                f.write(data)
            myprint(f"Please modify {agent_cfg.workspace}/grok.token and reset your API KEY\n")
            exit(-1)
        else:
            myprint(e)
            time.sleep(3)
            continue
    
    # format output
    reply = completion.choices[0].message
    messages.append(reply)
    if reply.tool_calls:
        for tool_call in reply.tool_calls:
            # myprint(tool_call.to_json())
            if tool_call.function.name == "batch":
                tool_active = 1
                # myprint(tool_call.function.arguments)
                args = json.loads(tool_call.function.arguments)
                agent_think = args.get("think")
                agent_cmd = args.get("command")

                # DECODE HTML entities if Grok accidentally encodes them
                agent_cmd = html.unescape(agent_cmd)
                save_message.append(f"<assistant>tool=batch, think={agent_think}, cmd=\n{agent_cmd}\n</assistant>\n")
                print_agent_tool(agent_think, agent_cmd)

                if confirm_need:
                    if grok_file:
                        confirm_info = get_grok_input_from_file() 
                    else:
                        confirm_info = input()
                else:
                    confirm_info = ''

                if not confirm_info or confirm_info.lower().startswith('y'):
                    ret = subprocess.run(agent_cmd,
                        text=True,
                        shell=True,
                        capture_output=True)
                    tool_result = f"returncode={ret.returncode}, stdout={ret.stdout}, stderr={ret.stderr}"
                else:
                    tool_result = f"returncode=-1, stderr=user temporarily declined tool call once."\
                                  f"reason: **{confirm_info}**."\
                                  f"you need to think why you did it wrong."\
                                  f"try to use a correct alternative."
                myprint(tool_result)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
                save_message.append(f"<tool_result>{tool_result}</tool_result>\n")
                continue # 
    elif reply.content:
        save_message.append(f"<assistant>{reply.content}</assistant>\n")
        print_content = reply.content.rstrip("\n$")
        myprint(f"{'-'*60}\nGrok: {print_content}", end=f'\n{'-'*60}\n$ ')
    
    # avoid conversation too long
    if len(messages) > 100:
        messages = messages[:2] + messages[-95:]
        save_message = save_message[-95:]
    



