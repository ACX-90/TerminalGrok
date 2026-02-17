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
export workspace="/home/${USERNAME}/TerminalGrok"

# enter API key
if [ ! -f "${workspace}/grok.token" ]; then
    read -p "Enter your OPENROUTER_API_KEY: " api_key
    echo ${api_key} > ${workspace}/grok.token
    echo "Your API KEY saves in ${workspace}/grok.token"
fi

if [ ! -d "${workspace}" ]; then
    echo "Creating Grok"
    mkdir "${workspace}"
fi

if [[ ${PWD} != ${workspace} ]] then
    cp *.py "${workspace}/"
    cp *.sh "${workspace}/"
fi

if [ ! -d "${workspace}/venv" ]; then
    echo "Setup Python"
    python3.12 -m venv "${workspace}/venv"
    "${workspace}/venv/bin/pip" install openai
    "${workspace}/venv/bin/pip" install "httpx[socks]"
    echo "Python virtual environment done"
fi
 
echo "Start Grok"
cd "${workspace}"
"${workspace}/venv/bin/python" "${workspace}/main.py"

