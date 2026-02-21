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

if [ ! -d "${workspace}" ]; then
    echo "Creating Grok"
    mkdir "${workspace}"
fi

# enter API key
if [ ! -f "${workspace}/tokens/grok.token" ]; then
    read -p "Enter your OPENROUTER API_KEY: " api_key
    if [ ! -d "${workspace}/tokens" ]; then
    	mkdir "${workspace}/tokens"
    fi
    echo ${api_key} > ${workspace}/tokens/grok.token
    echo "Your API KEY saves in ${workspace}/tokens/grok.token"
fi

if [ ! -f "${workspace}/tokens/agent00.token" ]; then
    read -p "Enter your Telegram API_KEY: " api_key
    echo ${api_key} > ${workspace}/tokens/agent00.token
    echo "Your API KEY saves in ${workspace}/tokens/agent00.token"
fi


if [[ ${PWD} != ${workspace} ]] then
    if [ ! -d "${workspace}/src" ]; then
    	mkdir "${workspace}/src"
    fi
    if [ ! -d "${workspace}/config" ]; then
    	mkdir "${workspace}/config"
    fi
    cp ./src/*.py "${workspace}/src/"
    cp ./config/*.cfg "${workspace}/config/"
    cp *.sh "${workspace}/"
fi

if [ ! -d "${workspace}/venv" ]; then
    echo "Setup Python"
    sudo apt install python3.12-venv
    python3.12 -m venv "${workspace}/venv"
    "${workspace}/venv/bin/pip" install "openai"
    "${workspace}/venv/bin/pip" install "httpx[socks]"
    "${workspace}/venv/bin/pip" install "python-telegram-bot"
    "${workspace}/venv/bin/pip" install "python-telegram-bot[job-queue]"
    echo "Python virtual environment done"
fi
 
echo "Start Grok"
cd "${workspace}"
"${workspace}/venv/bin/python" "${workspace}/src/main.py"

