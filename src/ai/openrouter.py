import re
import copy
import time
import os
import json
import html
import subprocess
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
if glb.ai_vendor == 'openrouter':
    try:
        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=glb.grok_token,
        )
    except Exception as e:
        print(f"OpenAI socks fail {e}")
        exit(-1)


def chat(*args, **kwargs) -> str:
    if glb.ai_vendor != 'openrouter':
        return "ERROR: OpenRouter client not initialize."
    model = None
    messages = None
    tool_choice = None
    tools = None
    temperature = 0.7

    for x, v in kwargs.items():
        match x:
            case "model":
                model = v
            case "messages":
                messages = v
            case "tool_choice":
                tool_choice = v
            case "tools":
                tools = v
            case "temperature":
                temperature = v

    completion = client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice=tool_choice,
        temperature=temperature,
    )
    content = completion.choices[0].message.content
    reasoning = completion.choices[0].message.reasoning
    tool_calls = completion.choices[0].message.tool_calls
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


def init(**kwargs):
    if glb.ai_vendor != 'openrouter':
        return "ERROR: OpenRouter client not initialize."

def reset(**kwargs):
    if glb.ai_vendor != 'openrouter':
        return "ERROR: OpenRouter client not initialize."


def ai_register():
    return {
        "name": "openrouter",
        "description": "openrouter's API",
        "chat": chat,
        "init": init,
        "reset": reset,
    }
