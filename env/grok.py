#!/usr/bin/env python3

# This script is used to communicate with Grok by terminal command.
# $ grok will poll the existing messages and send to your terminal
# $ grok "your message" will send message to grok and wait for reply,
# then print the reply in terminal.

import os
import sys
import time

workspace = "/home/crydiaa/TerminalGrok"
reply = workspace + "/fcomm/reply.grok"
msg = workspace + "/fcomm/msg.grok"
endkey = "<GROK status=end/>"
rxkey = "<GROK status=done/>"
txkey = "<GROK status=start/>"

# check if there is message from Grok, if so print the message and remove the file.
if os.path.isfile(reply):
    print("Grok has message.")
    with open(reply, "r") as f:
        for line in f:
            line = line.strip()
            if line not in (rxkey, endkey):
                print(line)
    os.remove(reply)
else:
    print("Grok is not ready.")

# only when there is message from terminal, send the message to Grok and wait for reply.
if len(sys.argv) > 1:
    # if there is message from terminal, send the message to Grok and wait for reply.
    with open(msg, "w") as f:
        data = " ".join(sys.argv[1:]) + "\n" + txkey + "\n"
        f.write(data)
    # when done flag is received, print the message in terminal.
    # when end flag is received, stop waiting and exit.
    end_transfer = 0
    while not end_transfer:
        if not os.path.isfile(reply):
            print("*", end="", flush=True)
            time.sleep(0.5)
            continue
        with open(reply, "r") as f:
            for line in f:
                line = line.strip()
                if line not in (rxkey, endkey):
                    print(line)
                if line.find(endkey) != -1:
                    end_transfer = 1
                    break
        os.remove(reply)

    
