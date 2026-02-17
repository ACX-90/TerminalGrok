bash = {
        "type": "function",
        "function": {
            "name": "bash",
            "description": """Execute bash commands in the user's terminal. 
                            CRITICAL: Generate commands with RAW shell syntax:
                            - Use < > not &lt; &gt;
                            - Use && not &amp; &amp;
                            - Use | not &pipe;
                            - Use " not &quot; 
                            - **NEVER use cd, Use only absolute path**
                            - **NEVER use && and other command after EOF**
                            NEVER HTML-encode the command string. Output raw bash syntax only.""",
            "parameters": {
                "type": "object",
                "properties": {
                    "think": {
                        "type": "string",
                        "description": "You must think carefully what's the best bash command to do, **you must do it step by step**, check previous result every step, **you must not output dangerous bash command**, write your thoughts",
                    },
                    "command": {
                        "type": "string",
                        "description": "Raw bash command with proper shell syntax (no HTML encoding)"
                    }
                },
                "required": ["think", "command"]
            }
        }
    }

file_edit = {
        "type": "function",
        "function": {
            "name": "file_edit",
            "description": """Choose one file, """,
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "name of the file you want to read or write"
                    },
                    "command": {
                        "type": "string",
                        "description": "operation, read; write; "
                    }
                },
                "required": ["filename", "command"]
            }
        }
    }
