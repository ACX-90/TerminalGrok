import os
import time

import xai_sdk
from xai_sdk import Client
from xai_sdk.chat import user, system, tool
from xai_sdk.tools import web_search
from xai_sdk.tools import x_search

import global_cfg as glb
import general as gen

if glb.ai_vendor == 'xai':
    if not os.path.isfile(glb.xai_token_file):
        print("Input your xAI API key:")
        xai_token = input().strip()
        with open(glb.xai_token_file, "w") as f:
            f.write(xai_token)
    else:
        with open(glb.xai_token_file, "r") as f:
            xai_token = f.read().rstrip(' \n')
    client = Client(
        api_key=xai_token,
        timeout=3600
        )
else:
    client = None

# default tools provided by xAI
default_tools = [
   web_search(), 
   # x_search(),
]
# converted from openai format
converted_tools = []
# if there are tools, use default_tools + converted_tools, if not, just use default_tools
current_tools = None

previous_response_id = None

chat_history = []

def chat(*args, **kwargs) -> str:
    if glb.ai_vendor != 'xai':
        return "ERROR: xAI client not initialize."
    global current_tools
    model = "grok-4-1-fast-reasoning"
    messages = None
    tools = None
    tool_choice = None
    temperature = 0.7
    mode = "main"
    for x, v in kwargs.items():
        match x:
            case "model":
                if v.startswith("grok"):
                    model = v
                # else may be openrouter format, ignore the prefix
            case "messages":
                messages = v
            case "tool_choice":
                tool_choice = v
            case "tools":
                tools = v
                converted_tools = []
                for single_tool in tools:
                    converted_tools.append(tool(
                        name=single_tool["function"]["name"],
                        description=single_tool["function"]["description"],
                        parameters=single_tool["function"]["parameters"]
                       ))
                current_tools = default_tools + converted_tools
            case "temperature":
                temperature = v
            case "mode":
                mode = v
    match mode:
        case 'aux':
            grok_chat = client.chat.create(
                model=model,
                store_messages=False,
                temperature=temperature,
            )
            grok_chat.append(system(messages[0]["content"]))
        case 'main':
            grok_chat = client.chat.create(
                model=model,
                tools=current_tools,
                # tool_choice=tool_choice,
                previous_response_id=previous_response_id,
                include=["verbose_streaming"],
                store_messages=True,
                temperature=temperature,
            )
        case 'code':
            return "Code mode not supported yet."
    if previous_response_id is None:
        grok_chat.append(system(messages[0]["content"]))
    # add user chat
    if messages and len(messages) > 1:
        # use xAI chat memory
        grok_chat.append(user(messages[-1]["content"]))
    message = grok_chat.sample()
    content = gen.ai_to_html_reparse(message.content)
    reasoning = message.reasoning_content
    tool_calls = message.tool_calls
    tools = []
    if tool_calls:
        for tool_call in tool_calls:
            tools.append({
                "id": tool_call.id,
                "type": "function",
                "function": {
                    "name": tool_call.function.name,
                    "arguments": tool_call.function.arguments,
                },
            })
    return {
        "role": "assistant",
        "content": content,
        "reasoning": reasoning,
        "tool_calls": tools
    }

def init(*args, **kwargs):
    return

def reset(*args, **kwargs):
    if not client:
        return "ERROR: xAI_SDK not initialize."
    global previous_response_id
    previous_response_id = None
    return

def ai_register():
    return {
        "name": "xai",
        "description": "xAI's API",
        "chat": chat,
        "init": init,
        "reset": reset,
    }
