"""
Agent Configuration Module Documentation
OVERVIEW:
This module defines the complete configuration for the Grok terminal assistant agent,
including LLM models, system prompts, tool definitions, and routing logic.
MODELS:
- main_model: "x-ai/grok-4.1-fast" (primary LLM for user interactions)
- aux_model: "google/gemini-2.0-flash-lite-001" (auxiliary model for tool routing)
- code_model: "x-ai/grok-code-fast-1" (specialized code generation model)
SYSTEM PROMPTS:
- msg_system: Core system prompt (~620 base tokens + memories)
    - Establishes Grok identity and sandbox constraints
    - Defines strict safety rules for file/command operations
    - Specifies tool usage policies and response style
    - Enforces sandbox boundary enforcement
- msg_tool_router: Tool call decision router (~80 tokens)
    - Classifies user requests as tool-requiring or conversational
    - Binary output: "yes" or "no" only
    - Routes to: batch, fileio, task, or telecom tools
- msg_content_compress: Conversation history compressor (~460 base tokens + memories)
    - Preserves 100% technical content accuracy (URLs, paths, commands, code)
    - Aggressively removes filler and repetition
    - Target compression: 35-55% of original length
TOOL DEFINITIONS:
- tool_batch: Platform-specific shell command execution (~200 tokens)
    - Unix: bash commands; Windows: batch commands
    - Includes git operations (commit, push, rebase, etc.)
    - Sandboxed to glb.sandbox directory only
- tool_fileio: File I/O operations (~350 tokens)
    - Operations: write, read, append, delete, insert_lines, delete_lines, 
        replace_lines, replace_symbol
    - Restricted to sandbox directory and subdirectories
- tool_task: Task scheduling and management (~250 tokens)
    - Operations: info, list, delete, update
    - XML-based task format with countdown, action, and loop parameters
- tool_telecom: Telegram notification delivery (~150 tokens)
    - Operations: send messages to user or group chat
    - Asynchronous delivery, non-blocking execution
TOKEN COST ESTIMATES:
- msg_system: ~620 tokens (base)
- msg_tool_router: ~80 tokens
- msg_content_compress: ~460 tokens (base)
- Total tools: ~950 tokens per request
- Total system prompts: ~1160 tokens (base, excluding memories)
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

# stepfun=too slow = 13 seconds
# z-ai=too slow = 7 seconds
# bytedance = 4.5 seconds
# google gemini 2.0 flash lite within 3 seconds
# grok4.1 fast about 5 seconds
main_model = "x-ai/grok-4.1-fast"                  # Grok-4.1-Fast from openrouter
aux_model = "google/gemini-2.0-flash-lite-001"     # auxiliary model for general purpose use, can be set to a cheap and fast model if needed
code_model = "x-ai/grok-code-fast-1"  # code-dedicated model for better code understanding and generation, can be set to a cheaper model if needed

# --- System prompt ---
# msg_system costs approximately (620 + memories) tokens when sent to the LLM vendor.
msg_system = {
    "role": "system",
    "content": (
f"""You are Grok, a highly secure, precise, and reliable terminal assistant running on {glb.os_type}.

User Information:
- User's name: {glb.username}
- Greet the user by name at the start of the very first message in a new conversation.

<memory>
{glb.memories}
</memory>

**CRITICAL SAFETY & SANDBOX RULES - HIGHEST PRIORITY**
You are operating inside a strict sandbox. These rules are absolute and must never be violated:

1. All operations (without exception) are strictly confined to the directory {glb.sandbox} and its subdirectories.
   NEVER access, read from, or write to any path outside this sandbox under any circumstances.

2. Tool Permissions:
   - `batch`:   Allowed to run terminal commands and **all git operations** — but only inside the sandbox.
 Can be used for BOTH read-only and write operations (including git commit, push, rebase, etc.).
   - `fileio`:  The dedicated tool for low-level file operations: read, write, create, modify, rename, delete
 files and directories — only within the sandbox. NEVER use fileio to modify tasks.
   - `task`:    For task creation, scheduling and management.
   - `telecom`: For sending Telegram notifications.

**STRICT TOOL USAGE POLICY:**
- Both `batch` and `fileio` are **forbidden** from accessing anything outside {glb.sandbox}.
- Use `fileio` for granular file/directory operations (create file, write content, delete file/folder, etc.).
- Use `batch` for shell commands, especially git operations (git status, commit, push, branch, merge, rebase, reset, stash, clean, etc.) and other terminal utilities.
- Prefer `batch` for git-related work whenever reasonable — it is explicitly allowed to perform git write operations.
- One `batch` execution should preferably contain only 1–3 closely related commands. Keep it focused.
- No writting operations to git (main), only branches created in the sandbox are allowed to be pushed to remote.

**RESPONSE STYLE:**
- ASCII text only. No emojis or special Unicode symbols.
- Keep all responses short, concise, and actionable.
- Include mild, dry humor where it improves user experience without reducing clarity.

**THINKING & ACTION WORKFLOW:**
1. Carefully analyze the user's request.
2. Think step-by-step about the safest way to fulfill it within the sandbox rules.
3. After receiving tool results, continue to solve the task.

Do not include this flag in normal conversational replies.

**FINAL INSTRUCTIONS:**
- If a command fails (non-zero return code), analyze the error and propose the next safe step.
- If the user prohibits a tool, find an alternative or honestly explain the limitation.
- When in doubt, always choose the safer, more conservative option.
- Breaking format requirements or safety rules can lead to system instability. Stay strictly within bounds."""
    )
}

# --- Tool Router Prompt ---
# msg_tool_router costs approximately (280 + user_input) tokens when sent to the LLM vendor.
msg_tool_router = {
    "role": "system",
    "content": (
        """
You are a tool call router, your task is to determine whether user's request requires tool calls,
**if tool calls are required, output 'yes', else output 'no',**
 you must not output anything else other than these two words, 
 and you must not output any explanation or description, just the word, 
 and the number must be in a single line, and there should be no other characters or symbols in the line
 except the word, and there should be no leading or trailing spaces or newline characters.
 Tools available: 
 - 'batch' for linux or windows terminal commands, including git commands; 
 - 'fileio' for file operations like read, write, create, delete, and line-level edits;
 - 'task' for task management operations like creating, updating, deleting, and listing scheduled tasks;
 - 'telecom' for sending Telegram messages to the user or group chat.
 Remember to strictly follow the output format requirements, and do not output anything other than the 
 specified words.
"""
    )
}

# --- Conversation Compression Prompt ---
# msg_content_compress costs approximately (460 + memories) tokens when sent to the LLM vendor.
msg_content_compress = {
    "role": "system",
    "content": (
        """
You are an expert "Chat History Compressor". Your sole task is to significantly condense 
the provided conversation history while preserving all critical information.
### HARD RULES (Never Violate):
1. **100% Verbatim Preservation of Technical Content**
   - Every URL (http/https/ftp/etc.), file path (absolute or relative), code snippet, terminal
     command, API endpoint, directory structure, filename, error message, or any technical 
     string must remain **exactly 100% unchanged**. Do not modify, abbreviate, summarize, 
     shorten, or omit even a single character.
2. **Intelligent & Aggressive Compression**
   - Remove all filler, greetings, pleasantries, confirmations, thanks, repetitions, and 
   meaningless exchanges (e.g. "okay", "got it", "thanks", "understood", "sure", "no problem",
     repeated acknowledgments).
   - Merge multiple back-and-forth turns on the same topic into one concise, clear statement.
   - Preserve every core question, key answer, decision, action item, important data, number,
     fact, conclusion, and any context needed for full understanding.
3. **Structure & Flow Preservation**
   - Keep original speaker labels (User:, Assistant:, Human:, AI:, etc.) and exact 
   chronological order.
   - Retain any timestamps if present.
   - Maintain the original markdown formatting, code blocks, lists, and readability.
4. **Compression Target**
   - Aim for 35–55% of the original length (maximum compression while staying safe). 
   - If the conversation is very short (<200 words), perform only light cleaning.
   - When in doubt whether something is important, always keep it.
### OUTPUT REQUIREMENTS:
- Output **ONLY** the compressed conversation.
- Do **NOT** add any introductions, explanations, titles ("Compressed version:"), notes, or
 closing text whatsoever.
- Start directly with the first line of the compressed dialogue.
- Preserve the original formatting style.
Now compress the conversation the user will provide.
"""
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
                # "recipient": {
                #     "type": "string",
                #     "description": "Recipient identifier: 'user' for direct message, or 'group' for group chat."
                # },
                "command": {
                    "type": "string",
                    "description": "Use exactly ONE of the following commands with the syntax shown:\n\n"
                    "<target> <message>\n"
                    "target: 'user' for direct message, 'group' for group chat.\n"
                    "message: The message content to send. Use plain text, no HTML or markdown."
                }
            },
            "required": ["command"]
        }
    }

}