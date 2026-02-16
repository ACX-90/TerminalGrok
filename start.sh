#!/bin/bash

# config PROXY
unset ALL_PROXY
unset all_proxy
unset http_proxy
unset https_proxy
unset ALL_PROXY_SOCKS
export ALL_PROXY="socks5://127.0.0.1:7890"
export all_proxy="socks5://127.0.0.1:7890"
export http_proxy="http://127.0.0.1:7890"
export https_proxy="http://127.0.0.1:7890"

# general
workspace="/home/${USERNAME}/TerminalGrok"
export grok_workspace="${workspace}"

# enter API key
if [ ! "${OPENROUTER_API_KEY}" ]; then
    read -p "Enter your OPENROUTER_API_KEY: " api_key
    export OPENROUTER_API_KEY="${api_key}"
    echo "export OPENROUTER_API_KEY=\"${api_key}\"" >> ~/.bashrc
    source ~/.bashrc
    echo "Your API KEY is: ${OPENROUTER_API_KEY}"
else
    echo "API_KEY Found"
fi

if [ ! -d "${workspace}" ]; then
    echo "Creating Grok"
    mkdir "${workspace}"
fi

cp main.py "${workspace}/main.py"
cp start.sh "${workspace}/start.sh"
    
if [ ! -d "${workspace}/venv" ]; then
    echo "Setup Python"
    python3.12 -m venv "${workspace}/venv"
    "${workspace}/venv/bin/pip" install openai
    "${workspace}/venv/bin/pip" install "httpx[socks]"
    echo "Python virtual environment done"
else
    echo "Python virtual environment found"
fi
 
echo "Start Grok"

"${workspace}/venv/bin/python" "${workspace}/main.py"

