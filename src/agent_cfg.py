"""
Configuration module for the Grok terminal assistant agent.
This module sets up the necessary configurations for the Grok AI assistant, including:
- Loading the API token from a file.
- Retrieving previous conversation memories.
- Defining the system prompt with user-specific details and strict rules.
- Configuring tools for batch commands (platform-specific), file I/O operations, and task management.
All operations are restricted to a sandboxed workspace for security.
"""
import os
import sys
import global_cfg as glb

# --- Models config ---
# model from openrouter, can be modified to other vendors' models if needed
# compress_model user openrouter's free model, which can be used for compressing
# conversation history to save token, but currently not implemented yet
model = "x-ai/grok-4.1-fast"            # Grok-4.1-Fast from openrouter
compress_model = "openrouter/free"

# --- System prompt ---
# msg_system costs approximately 400 tokens when sent to the LLM vendor.
msg_system = {
    "role": "system",
    "content": (
        f"You are Grok, a terminal assistant running on {glb.os_type}.\n"
        f"The user's name is {glb.username}. Greet them at the start of the conversation.\n\n"
        f"<memory>\n{glb.memories}\n</memory>\n\n"
        "**Rules you must follow**:\n"
        "- ASCII only, no emoji. Keep responses short, precise, with mild humor.\n"
        f"- Workspace is strictly limited to {glb.sandbox} and its subdirectories. NEVER access paths outside this.\n"
        "- You have access to three tools: `batch` for read-only terminal commands, `fileio` for file operations,"
        " and `task` for task management.\n"
        "- Use the `batch` tool ONLY for read-only operations: directory listing, reading file content, "
        "simple checks, environment queries, and other non-destructive actions.\n"
        "- NEVER use `batch` to create, modify, append, overwrite, or delete file contents.\n"
        "- ALL file content changes must be done exclusively via the `fileio` tool.\n"
        "- Use the `task` tool for scheduling and managing tasks within the sandbox.\n"
        "- One `batch` call = at most 1-2 simple actions. Think step by step.\n"
        "- On non-zero return code: analyze the error and decide the next step.\n"
        "- If the user forbids a tool: find an alternative or explain why the task is impossible.\n"
        "- Your workflow is: analyze the situation, decide what to do,"
        f" if tools are needed, you can output the require flag **{glb.grok_tool_req_flag} in THE FIRST LINE of reply**.\n"
        " In the next round, decide how to use tools to finish tasks, "
        " **WARNING: NEVER break the rules above, if you are not sure, choose the safer option. "
        " Breaking any format requirement will cause system crash**"
    )
}

# --- Tool definitions ---
# Select batch tool based on platform
# tool_batch costs approximately 200 tokens when sent to the LLM vendor.
if sys.platform.lower().__contains__("win"):
    tool_batch = {
        "type": "function",
        "function": {
            "name": "batch",
            "description": (
                "Execute a READ-ONLY Windows Batch command in the user's terminal. "
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
    tool_batch = {
        "type": "function",
        "function": {
            "name": "batch",
            "description": (
                "Execute a READ-ONLY bash command in the user's terminal. "
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

# tool_fileio costs approximately 350 tokens when sent to the LLM vendor.
tool_fileio = {
    "type": "function",
    "function": {
        "name": "fileio",
        "description": (
            "Perform file read/write operations within the sandbox. "
            f"Use absolute paths starting with {glb.sandbox}, only operate within this directory and its subdirectories. "
            "Use this tool for ALL file content changes: create, write, append, delete, "
            "and line-level edits. Never use the batch tool for any of these operations."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Use exactly ONE of the following commands with the syntax shown:\n\n"
                        "write <path> <content>\n"
                        "  Create or overwrite a file with the given content.\n\n"
                        "read <path>\n"
                        "  Read and return the file content. Returns error if file not found.\n\n"
                        "append <path> <content>\n"
                        "  Append content to a file. Creates the file if it does not exist.\n\n"
                        "delete <path>\n"
                        "  Delete a file. Returns error if file not found.\n\n"
                        "insert_lines <path> <line_index> <content>\n"
                        "  Insert one or more lines before the given line index (1-based).\n"
                        "  After insertion, the new content starts at line_index.\n"
                        "  Returns error if file not found or line_index is out of range.\n\n"
                        "delete_lines <path> <line_index> <count>\n"
                        "  Delete exactly <count> lines starting from line_index (1-based).\n"
                        "  Returns error if file not found or range is out of bounds.\n\n"
                        "replace_lines <path> <line_index> <count> <content>\n"
                        "  Delete <count> lines starting from line_index, then insert <content> "
                        "at that position. Replacement may have a different line count than <count>.\n"
                        "  Returns error if file not found or range is out of bounds.\n\n"
                        "replace_symbol <path> <symbol> <content>\n"
                        "  Replace all occurrences of <symbol> in the file with <content>. "
                        "Returns error if file or symbol not found.\n\n"
                        "Note: <content> is treated as a single argument. "
                        "Multiple lines of content should be separated by \n"
                    )
                }
            },
            "required": ["command"]
        }
    }
}

# tool_task costs approximately 250 tokens when sent to the LLM vendor.
tool_task = {
    "type": "function",
    "function": {
        "name": "task",
        "description": (
            "Perform task management operations within the sandbox. "
            "Tasks are scheduled actions that can be executed after a countdown or at intervals. "
            "Use this tool for ALL task operations: create, read, update, delete, and list. "
            "All tasks are in XML format. "
            "all time units are in seconds. loop is optional, if enable=0, the task will not loop. "
            "any time interval shorter than 60 seconds will forced to be 60 seconds to prevent abuse. "
            "remain is the total execution times for the task, when remain is -1, it means infinite loop."
            "interval is the time between each execution. "
            "**DO NOT add or delete XML tags, strictly follow the format.** "
            "Task file format example:\n\n"
            "<?xml version='1.0' encoding='utf-8'?>"
            "<task>"
            "<countdown>60</countdown>"
            "<action><![CDATA[**prompt for grok of what to do when task activated**]]></action>"
            "<loop>"
            "<enable>1</enable>"
            "<interval>60</interval>"
            "<remain>5</remain>"
            "</loop>"
            "</task>"
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": (
                        "Use exactly ONE of the following commands with the syntax shown:\n\n"
                        "info <task_name>\n"
                        "  Read and return the content of the specified task file. "
                        "Returns error if the task file does not exist.\n\n"
                        "list\n"
                        "  List all existing task files in the tasks directory. "
                        "Returns a list of task names with the .task extension.\n\n"
                        "delete <task_name>\n"
                        "  Delete the specified task file. Returns error if the task file does not exist.\n\n"
                        "update <task_name> <content>\n"
                        "  Create or overwrite the specified task file with the given content. "
                        "Content should be in XML format. Returns error if content is not valid XML."
                    )
                }
            },
            "required": ["command"]
        }
    }
}

# tool_telecom costs approximately 150 tokens when sent to the LLM vendor.
tool_telecom = {
    "type": "function",
    "function": {
        "name": "telecom",
        "description": (
            "Send a Telegram message to the user or to a group chat. "
            "Use this tool to notify the user of task completion, errors, or important information. "
            "Messages are sent asynchronously and do not block execution."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "recipient": {
                    "type": "string",
                    "description": "Recipient identifier: 'user' for direct message, or 'group' for group chat."
                },
                "message": {
                    "type": "string",
                    "description": "The message content to send. Use plain text, no HTML or markdown."
                }
            },
            "required": ["recipient", "message"]
        }
    }

}