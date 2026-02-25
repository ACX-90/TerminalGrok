import subprocess
import sys
import global_cfg as glb

# tool_batch costs approximately 200 tokens when sent to the LLM vendor.
if sys.platform.lower().__contains__("win"):
    tool_define_batch = {
        "type": "function",
        "function": {
            "name": "batch",
            "description": (
                "Execute a Windows Batch command in the user's terminal. "
                "**When user require to search or list files in sandbox, must use this tool. **"
                "Allowed uses: directory listing, reading file content (type), simple checks, "
                "environment queries, and other non-destructive operations. "
                "NEVER use this tool to create, modify, append, overwrite, or delete any file. "
                "Use raw Windows Batch syntax only — no HTML encoding. "
                "Rules: "
                f"(1) NEVER use 'cd'; use absolute paths starting with {glb.sandbox}. "
                "(2) NEVER chain commands after EOF with &&. "
                "(3) One call = at most 1-2 simple actions. "
                "(4) Output raw syntax: use < > not &lt; &gt;, use && not &amp;&amp;, "
                "use | not &pipe;, use \" not &quot;."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Raw Windows Batch command with proper syntax (no HTML encoding)."
                    }
                },
                "required": ["command"]
            }
        }
    }
else:
    tool_define_batch = {
        "type": "function",
        "function": {
            "name": "batch",
            "description": (
                "Execute a bash command in the user's terminal. "
                "**When user require to search or list files in sandbox, must use this tool. **"
                "Allowed uses: directory listing, reading file content (cat), simple checks, "
                "environment queries, and other non-destructive operations. "
                "NEVER use this tool to create, modify, append, overwrite, or delete any file. "
                "Use raw bash syntax only — no HTML encoding. "
                "Rules: "
                f"(1) NEVER use 'cd'; use absolute paths starting with {glb.sandbox}. "
                "(2) NEVER chain commands after a heredoc EOF with &&. "
                "(3) One call = at most 1-2 simple actions. "
                "(4) Output raw syntax: use < > not &lt; &gt;, use && not &amp;&amp;, "
                "use | not &pipe;, use \" not &quot;."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Raw bash command with proper shell syntax (no HTML encoding)."
                    }
                },
                "required": ["command"]
            }
        }
    }

tool_brief_batch = """Run terminal commands and **all git operations**. """

tool_rule_batch = """Must only used in sandbox, unless user give you permission to access other directories.
NEVER use `batch` to create, modify, append, overwrite, or delete any file.
Must use this tool for sandbox file seraching and listing. """

# tool_handle_batch:
# handle the batch tool call from grok, currently just print the command and thought, and ask for confirm
def tool_handle_batch(cmd):
    try:
        ret = subprocess.run(cmd, text=True, shell=True, capture_output=True)
        ret = f"returncode={ret.returncode}, stdout={ret.stdout}, stderr={ret.stderr}"
    except Exception as e:
        ret = f"ERROR: Exception occurred while executing batch command. Exception: {e}"
    return ret

def tool_register():
    return {
        "name": "batch",
        "description": "Batch processing tool for executing multiple tasks sequentially. ",
        "handler": tool_handle_batch,
        "definition": tool_define_batch,
        "prompt": {
            "brief": tool_brief_batch,
            "rule": tool_rule_batch
        }
    }