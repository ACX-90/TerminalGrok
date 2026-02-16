import time
import os
os.environ['ALL_PROXY'] = 'socks5://127.0.0.1:7890'
os.environ['all_proxy'] = 'socks5://127.0.0.1:7890'
os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:7890'
os.environ['HTTP_PROXY'] = 'http://127.0.0.1:7890'
from openai import (
    OpenAI,
    AuthenticationError,
)

workspace = os.getenv('grok_workspace')
username = os.getenv('USERNAME')
api_key = os.getenv("OPENROUTER_API_KEY")
mem_file = f"{workspace}/memories.txt"

try:
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )
except Exception as e:
    print("OpenAI socks fail")
    print(e)
    exit(-1)

try:
    with open(mem_file, "r", encoding="utf-8") as f:
        memories = f.read()
except FileNotFoundError:
    memories = "No previous conversation"
    
model = "x-ai/grok-4.1-fast"
default_message = [
    {
        "role": "system",
        "content": "<role>You are Grok, an assistant live in Ubuntu terminal.</role>"
                   "<style>Your reply use only ASCII, be short and precise, humor.</style>"
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
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
        )
    except Exception as e:
        if isinstance(e, AuthenticationError):
            print("Error: Invalid API KEY")
            userconfig = f"/home/{username}/.bashrc" 
            data = open(userconfig, "r").read()
            data = data.replace("export OPENROUTER_API_KEY=", "export OPENROUTER_INVALID_KEY=")
            open(userconfig, 'w').write(data)
            print("Please modify ~/.bashrc and reset your OPENROUTER_API_KEY\n"
                  "Use source ~/.bashrc to refresh API KEY\n"
                  "Close and reopen your terminal after that\n")
            exit(-1)
        else:
            print(e)
            time.sleep(3)
            continue
    
    # print hint
    if cnt == 0:
        print(f"/r: Reset session    /q: Quit    /m: Save memory    /cm: Clear memory")
    
    # format output
    reply = completion.choices[0].message
    print_content = reply.content.rstrip("\n$")
    print(f"\nGrok: {print_content}", end='\n$')
    messages.append(reply)
    save_message.append(f"<assistant>{reply.content}</assistant>\n")
    
    # avoid conversation too long
    if len(messages) > 30:
        messages = messages[:2] + messages[-20:]
        save_message = save_message[-20:]
    cnt += 1




