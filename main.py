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

# prepare global variables
debug = 0

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

confirm_need = 1
save_message = []
messages = default_message
initial = 1
tool_active = 0
current_tools = 0
tool_result = ''
while True:
    # print hint
    if initial == 1:
        initial = 0
        print(f"/r: Reset session    /q: Quit    /m: Save memory    /cm: Clear memory")
        print(f"/b: Grok Batch  /c: Confirm Need  /n: NoConfirm")
        messages = default_message
    elif tool_active:
        tool_active = 0
        current_tools = tools
    else:
        current_tools = 0
        tool_active = 0
        x = input()
        match x.lower():
            case '/r':
                initial = 1
                print("$", end=' ')
                continue
            case '/q':
                break
            case '/m':
                with open(agent_cfg.mem_file, 'a', encoding="utf-8") as f:
                    f.write("".join(save_message))
                save_message = []
                print("$", end=' ')
                continue
            case '/cm':
                with open(agent_cfg.mem_file, 'w', encoding="utf-8") as f:
                    f.write('')
                print("$", end=' ')
                continue
            case '/c':
                confirm_need = 1
                print("$", end=' ')
                continue
            case '/n':
                confirm_need = 0
                print("$", end=' ')
                continue
        if x.startswith('/b '):
            # example: /b output asdwerasdwer to file test.txt
            current_tools = tools
            tool_active = 1
            x = x[3:]
        messages.append({"role":"user", "content": x})
        save_message.append(f"<user>{x}</user>\n")
        
    # make conversation
    try:
        if debug:
            print("Grok is thinking...")
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=current_tools,
            tool_choice="auto" if current_tools else 0,
            temperature=0.0 if current_tools else 1.0,
        )
        if debug:
            print('Grok made a repy:')
    except Exception as e:
        if isinstance(e, AuthenticationError):
            print(e)
            print("Error: Invalid API KEY")
            data = "#error: " + agent_cfg.api_key
            with open(f"{agent_cfg.workspace}/grok.token", "w") as f:
                f.write(data)
            print(f"Please modify {agent_cfg.workspace}/grok.token and reset your API KEY\n")
            exit(-1)
        else:
            print(e)
            time.sleep(3)
            continue
    
    # format output
    reply = completion.choices[0].message
    messages.append(reply)
    if reply.tool_calls:
        for tool_call in reply.tool_calls:
            # print(tool_call.to_json())
            if tool_call.function.name == "batch":
                tool_active = 1
                # print(tool_call.function.arguments)
                args = json.loads(tool_call.function.arguments)
                agent_thk = args.get("think")
                agent_cmd = args.get("command")

                # DECODE HTML entities if Grok accidentally encodes them
                agent_cmd = html.unescape(agent_cmd)
                save_message.append(f"<assistant>tool=batch, cmd=\n{agent_cmd}\n</assistant>\n")
                print("\n" + "="*60)
                print(f"Grok's thought: {agent_thk}")
                print("-"*60)
                print("COMMAND TO EXECUTE:")
                print("-"*60)
                print(agent_cmd)
                print("="*60)
                print("Execute? (y/no and reasons): ", end="", flush=True)

                if confirm_need:
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
                print(tool_result)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": tool_result})
                save_message.append(f"<tool_result>{tool_result}</tool_result>\n")
                continue # 
    elif reply.content:
        save_message.append(f"<assistant>{reply.content}</assistant>\n")
        print_content = reply.content.rstrip("\n$")
        print(f"{'-'*60}\nGrok: {print_content}", end=f'\n{'-'*60}\n$ ')
    
    # avoid conversation too long
    if len(messages) > 40:
        messages = messages[:2] + messages[-35:]
        save_message = save_message[-35:]
    




