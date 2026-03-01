#!/bin/bash

# config PROXY for clash
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
export USERNAME="${USER}"
export workspace="/home/${USERNAME}/TerminalGrok"

# create workspace
if [ ! -d "${workspace}" ]; then
    echo "Creating Grok"
    mkdir -p "${workspace}"
fi

# enter OpenRouter API key for Grok
if [ ! -f "${workspace}/tokens/grok.token" ]; then
    read -p "Enter your OPENROUTER API_KEY: " api_key
    if [ ! -d "${workspace}/tokens" ]; then
    	mkdir "${workspace}/tokens"
    fi
    echo ${api_key} > ${workspace}/tokens/grok.token
    echo "Your API KEY saves in ${workspace}/tokens/grok.token"
fi

# enter Telegram API key for bot service
if [ ! -f "${workspace}/tokens/agent00.token" ]; then
    read -p "Enter your Telegram API_KEY: " api_key
    echo ${api_key} > ${workspace}/tokens/agent00.token
    echo "Your API KEY saves in ${workspace}/tokens/agent00.token"
fi

# copy files to workspace
if [[ ${PWD} != ${workspace} ]] then
    if [ ! -d "${workspace}/src" ]; then
    	mkdir "${workspace}/src"
    fi
    if [ ! -d "${workspace}/src/tools" ]; then
    	mkdir "${workspace}/src/tools"
    fi
    if [ ! -d "${workspace}/config" ]; then
    	mkdir "${workspace}/config"
    fi
    cp ./src/*.py "${workspace}/src/"
	cp ./src/tools/*.py "${workspace}/src/tools/"
    cp ./config/*.cfg "${workspace}/config/"
    cp *.sh "${workspace}/"
fi

# modify grok.py to workspace path and copy to /usr/bin
# enable to call grok anywhere in terminal
sed -i "s|workspace = \".*\"|workspace = \"${workspace}\"|" ./env/grok.py
sudo cp "./env/grok.py" /usr/bin/grok

# install python dependencies in virtual environment
if [ ! -d "${workspace}/venv" ]; then
    echo "Install python3.12-venv and create virtual environment"
    sudo apt install python3.12-venv
    python3.12 -m venv "${workspace}/venv"
    "${workspace}/venv/bin/pip" install "openai"
    "${workspace}/venv/bin/pip" install "xai_sdk"
    "${workspace}/venv/bin/pip" install "httpx[socks]"
    "${workspace}/venv/bin/pip" install "python-telegram-bot"
    "${workspace}/venv/bin/pip" install "python-telegram-bot[job-queue]"
    echo "Python virtual environment done"
fi
 
# start a grok instance
echo "Start Grok"
cd "${workspace}"
"${workspace}/venv/bin/python" "${workspace}/src/main.py"

