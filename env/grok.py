#!/usr/bin/env python3
import os
import sys
import time

workspace = "/home/crydiaa/TerminalGrok"
reply = workspace + "/fcomm/reply.grok"
msg = workspace + "/fcomm/msg.grok"
endkey = "<GROK status=end/>"
rxkey = "<GROK status=done/>"
txkey = "<GROK status=start/>"

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

if len(sys.argv) > 1:
    with open(msg, "w") as f:
        data = " ".join(sys.argv[1:]) + "\n" + txkey + "\n"
        f.write(data)
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

    
