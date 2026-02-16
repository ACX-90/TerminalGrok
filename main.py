import time
import os
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
workspace = os.getenv('grok_workspace')
username = os.getenv('USERNAME')
with open("grok.token", "r") as f:
    api_key = f.read().rstrip(' \n')
    if api_key.startswith("#error"):
        print("Error: you API is invalid")
        exit(-1) 
mem_file = f"{workspace}/memories.txt"

# setup openrouter client, or other vendors
try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
except Exception as e:
    print("OpenAI socks fail")
    print(e)
    exit(-1)

# read previous memories
try:
    with open(mem_file, "r", encoding="utf-8") as f:
        memories = f.read()
except FileNotFoundError:
    memories = "No previous conversation"

# model and prompts
model = "x-ai/grok-4.1-fast"
default_message = [
    {
        "role": "system",
        "content": "<role>You are Grok, an assistant live in Ubuntu terminal.</role>"
                   "<style>Your reply use only ASCII, no emoji, be short and precise, humor.</style>"
    },
    {
        "role": "assistant",
        "content": f"<memory>{memories}</memory>"
    },
    {
        "role": "system",
        "content": f"<action>Now say greetings to the user {username}.</action>"
    }, 
]
save_message = []
messages = default_message
cnt = 0

while True:
    # user input   
    if cnt == 0:
        messages = default_message
    else:
        x = input()
        match x.lower():
            case '/r':
                cnt = 0
                continue
            case '/q':
                break
            case '/m':
                with open(mem_file, 'a', encoding="utf-8") as f:
                    f.write("".join(save_message))
                save_message = []
                continue
            case '/cm':
                with open(mem_file, 'w', encoding="utf-8") as f:
                    f.write('')
                continue
        messages.append({"role":"user", "content": x})
        save_message.append(f"<user>{x}</user>\n")
    
    # print hint
    if cnt == 0:
        print(f"/r: Reset session    /q: Quit    /m: Save memory    /cm: Clear memory")
        print(f"/e: Execute bash")
        
    # make conversation
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as e:
        if isinstance(e, AuthenticationError):
            print("Error: Invalid API KEY")
            data = "#error: " + api_key
            with open("{workspace}/grok.token", "w") as f:
                f.write(data)
            print(f"Please modify {workspace}/grok.token and reset your API KEY\n")
            exit(-1)
        else:
            print(e)
            time.sleep(3)
            continue
    
    # format output
    reply = completion.choices[0].message
    print_content = reply.content.rstrip("\n$")
    print(f"\nGrok: {print_content}", end='\n$')
    messages.append(reply)
    save_message.append(f"<assistant>{reply.content}</assistant>\n")
    
    # avoid conversation too long
    if len(messages) > 40:
        messages = messages[:2] + messages[-35:]
        save_message = save_message[-35:]
    cnt += 1




