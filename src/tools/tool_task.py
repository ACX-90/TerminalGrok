"""
Module: tool_tasks.py
This module provides a comprehensive set of tools for managing scheduled tasks in a terminal-based
environment. It handles task creation, updating, deletion, listing, and retrieval, with tasks stored
as XML-formatted files. Tasks can be configured with countdown timers, actions (commands or prompts),
and looping behaviors for repeated execution.
Key Features:
- Task files are stored in a designated directory (taskdir), with each task named as '<task_name>.task'.
- XML structure includes elements for countdown (initial delay), action (executable command or Grok
 prompt), and loop settings (enable, interval, remain).
- Interval is enforced to a minimum of 60 seconds to prevent excessive resource usage.
- Supports infinite loops when remain is set to -1.
Available Tools:
1. update_task(task_name, content): Creates or updates a task file with provided XML content. Validates
 XML structure and required elements.
2. delete_task(task_name): Removes the specified task file from the directory.
3. list_tasks(): Returns a dictionary of all task names and their XML contents.
4. get_task_info(task_name): Retrieves the XML content of a specific task file.
5. execute_tasks_command(command): Parses and executes commands for task operations (update, delete, 
list, info).
6. tool_tasks_validate(): Runs validation tests for all command types to ensure functionality.
Usage:
- Tasks are intended for scheduling terminal commands or AI prompts with optional repetition.
- Commands are executed via the 'execute_tasks_command' function, supporting subcommands like 'update',
 'delete', 'list', and 'info'.
- Validation ensures XML integrity and prevents invalid configurations.
Dependencies: os, sys, time, xml.etree.ElementTree, global_cfg, general.
Note: This module is part of a larger system for task automation and should be used in conjunction with
 scheduling mechanisms.
"""
# python standard library
import os
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime

# project modules
import global_cfg as glb
import general as gen

# tool_task costs approximately 250 tokens when sent to the LLM vendor.
tool_define_task = {
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

tool_brief_task = """Manage scheduled tasks, includes creating, updating, deleting, and listing tasks. """

tool_rule_task = """Tasks are defined in **XML format and must include 'countdown', 'action', 'loop', 'enable', 'interval', 'remain' **. """

# =================================================================
# Tool task management
# =================================================================
# update_task:
# create a task file in taskdir, the content of the task file is defined by the user, and should
# be in xml format
# the task file should contain the following fields:
# - countdown: the time in seconds before the task is executed for the first time, after the task
# is created, the countdown field will be replaced by start_time field, which is the time when the
# task should be executed for the first time
# - action: the action to be executed when the task is activated, it can be any command that can
# be executed in the terminal, or any prompt for grok to do something when the task is activated
# - loop: the loop settings for the task, if enable is 1, the task will loop, and the interval field
# is the time in seconds between each execution, the remain field is the total execution times for
# the task, when remain is -1, it means infinite loop
# the task file should be in xml format, and the file name should be the task name with .task
# extension, for example, if the task name is "test", the file name should be "test.task"
# the task file format example:
# <?xml version='1.0' encoding='utf-8'?>
# <task>
#   <countdown>60</countdown>
#   <action>prompt for grok of what to do when task activated</action>
#   <loop>
#     <enable>1</enable>
#     <interval>60</interval>
#     <remain>5</remain>
#   </loop>
# </task>
def update_task(task_name, content):
    """Update task file in taskdir, the content of the task file is defined by the user,
      and should be in xml format, if the task file does not exist, create a new one, 
      if the task file already exists, update"""
    task_path = f"{glb.taskdir}/{task_name}.task"
    content = content.strip()
    content = content.strip('"')  # remove leading and trailing quotes if exist
    try:
        ET.fromstring(content)
    except ET.ParseError as e:
        return f"ERROR: Invalid XML format, ET parse error. {str(e)}"
    try:
        root = ET.fromstring(content)
        if root.tag != 'task':
            return "ERROR: Root element must be 'task'."
        countdown = root.find('countdown')
        action = root.find('action')
        loop = root.find('loop')
        if countdown is None or action is None or loop is None:
            return "ERROR: Missing required elements: countdown, action, or loop."
        enable = loop.find('enable')
        interval = loop.find('interval')
        remain = loop.find('remain')
        if enable is None or interval is None or remain is None:
            return "ERROR: Missing required elements in loop: enable, interval, or remain."
        # Check and adjust interval if shorter than 1 minute (60 seconds)
        interval_value = int(interval.text)
        if interval_value < 60:
            interval.text = '60'
            content = ET.tostring(root, encoding='unicode', xml_declaration=True)
            with open(task_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return "WARNING: Interval was less than 1 minute, set to 60 seconds. Task updated."
        with open(task_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return "SUCCESS: Task updated."
    except Exception as e:
        return f"ERROR: Failed to update task. {str(e)}"
    
# delete_task:
# delete a task file in taskdir, the file name should be the task name with .task extension, for example,
# if the task name is "test", the file name should be "test.task"
def delete_task(task_name):
    """Delete a task file in taskdir, the file name should be the task name with .task extension"""
    task_path = os.path.join(glb.taskdir, f"{task_name}.task")
    if not os.path.exists(task_path):
        return "ERROR: Task does not exist."
    try:
        os.remove(task_path)
        return "SUCCESS: Task deleted."
    except Exception as e:
        return f"ERROR: Failed to delete task. {str(e)}"
    
# list_tasks:
# list all task files in taskdir, and return the task names and their content in a dictionary format
# the dictionary format is {task_name: task_content}, where task_name is the name of the task without
# .task extension, and task_content is the content of the task file in xml format
def list_tasks():
    """List all task files in taskdir, and return the task names and their content in a dictionary
      format"""
    tasks = {}
    for file in os.listdir(glb.taskdir):
        if isinstance(file, str) and file.endswith('.task'):
            task_name = file[:-5]  # remove .task extension
            task_path = os.path.join(glb.taskdir, file)
            try:
                with open(task_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                tasks[task_name] = content
            except Exception as e:
                tasks[task_name] = f"ERROR: Failed to read task. {str(e)}"
    return tasks

# get_task_info:
# get the content of a task file in taskdir, the file name should be the task name with .task
# extension, for example, if the task name is "test", the file name should be "test.task"
def get_task_info(task_name):
    """Get the content of a task file in taskdir, the file name should be the task name with .task
      extension"""
    task_path = os.path.join(glb.taskdir, f"{task_name}.task")
    if not os.path.exists(task_path):
        return "ERROR: Task does not exist."
    try:
        with open(task_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"ERROR: Failed to read task. {str(e)}"


# process_new_task:
# Convert countdown to start_time for newly created tasks, and update the task file.
def process_new_task(load_task, current_task, task_path):
    current_task['loop'].update({'exec_count': {'#text': '0'}})
    """Convert countdown to start_time for newly created tasks"""
    count_down = float(current_task['countdown']['#text'])
    current_task.pop('countdown')
    start_time = time.time() + count_down
    current_task.update({'start_time': start_time})
    print(f"Daemon: Detected new task, converted countdown {count_down} to start_time {datetime.fromtimestamp(start_time)}, task details:")
    print(current_task)
    gen.dict_to_xml(load_task, task_path)

# execute_task:
# Execute a scheduled task and handle looping / cleanup logic afterward.
# Rules:
# - remain > 1:   execute → remain -= 1 → update start_time → save task file
# - remain = 1:   execute → delete task file
# - remain = 0:   do NOT execute → delete task file
# - remain = -1:  infinite loop → execute → update start_time → save (remain unchanged)
def execute_task(load_task, current_task, task_path, taskfile):
    # Extract key fields
    loop_section = current_task.get('loop', {})
    remain_str = loop_section.get('remain', {}).get('#text', '0')
    remain = int(remain_str)
    enable_str = loop_section.get('enable', {}).get('#text', 'false')
    is_loop_enabled = enable_str.lower() in ("1", "true", "yes", "t", "true")
    action_text = current_task.get('action', {}).get('#text', '(no action specified)')
    exec_count = int(current_task.get('loop', {}).get('exec_count', {}).get('#text', '0'))
    total_count = exec_count + remain
    interval_seconds = int(loop_section.get('interval', {}).get('#text', '60'))

    # ------------------ Decide whether to execute ------------------
    should_execute = True
    if remain == 0:
        should_execute = False
        print(f"Task {taskfile} has remain=0 → skipping execution, will delete file")
    elif remain > 0:
        print(f"Executing task: {action_text}  (remaining executions: {remain})")
        remain -= 1
    elif remain == -1:
        print(f"Executing task (infinite loop): {action_text}")
    else:
        # Invalid remain value
        print(f"Task {taskfile} has invalid remain value {remain} → skipping execution and deleting")
        should_execute = False

    # ------------------ Execute the task ------------------
    if should_execute:
        exec_count += 1
        current_task['loop']['exec_count']['#text'] = str(exec_count)
        if is_loop_enabled:
            if remain == -1:
                exec_info = '(Infinite)'
            else:
                exec_info = f"({exec_count}/{total_count})"
            exec_info += f' Per {interval_seconds} seconds'
        else:
            exec_info = f"(Once)"
        with open(glb.grok_fcomm_in_task, "w") as f:  # assuming 'agent' is available in scope
            f.write(f"<scheduled_task info='{exec_info}'>\n{action_text}</scheduled_task>\n{glb.grok_fcomm_start}")
            
    # ------------------ Post-execution cleanup / update ------------------
    if not is_loop_enabled:
        # Non-looping task: delete after execution (or if skipped)
        print(f"Task {taskfile} is not a looping task → deleting file")
        os.remove(task_path)
        return
    # From here: it's a looping task
    if remain == 0 or not should_execute:
        # No more executions allowed → delete
        print(f"Task {taskfile} has no remaining executions or invalid state → deleting file")
        os.remove(task_path)
        return
    # Still has executions left (remain == -1 or remain > 1)
    # Update next execution time
    try:
        interval_seconds = int(loop_section['interval']['#text'])
    except (KeyError, ValueError):
        interval_seconds = 300  # fallback: 5 minutes
        print(f"Warning: failed to read valid interval, using default {interval_seconds} seconds")
    current_task['start_time'] = time.time() + interval_seconds
    # Decrease counter only for finite loops
    if remain > 0:
        current_task['loop']['remain']['#text'] = str(remain)
    # Save updated task file
    gen.dict_to_xml(load_task, task_path)  # assuming this function exists and works correctly
    next_exec_time = datetime.fromtimestamp(current_task['start_time'])
    remaining_display = "infinite" if remain == -1 else str(remain)
    print(f"Task {taskfile} executed. Next run at {next_exec_time}, "
          f"remaining executions: {remaining_display}")

# daemon_task:
# Function that runs periodically, checks taskdir for .task files and executes them
def daemon_task():
    """Function that runs periodically, checks taskdir for .task files and executes them"""
    for taskfile in os.listdir(glb.taskdir):
        if not (isinstance(taskfile, str) and taskfile.endswith('.task')):
            continue
        task_path = os.path.join(glb.taskdir, taskfile)
        load_task = gen.xml_to_dict(task_path)
        current_task = load_task['task']
        start_time = float(current_task['start_time']['#text']) if current_task.__contains__('start_time') else 0
        if current_task.__contains__('countdown'):
            process_new_task(load_task, current_task, task_path)
        elif time.time() >= start_time:
            execute_task(load_task, current_task, task_path, taskfile)
        elif time.time() + 10 > start_time and time.time() + 9 < start_time:
            print(f"Task {taskfile} is scheduled to be executed at {datetime.fromtimestamp(start_time)}, "
                  f"which is in {start_time - time.time():.1f} seconds. Task details:")
            print(current_task)

# run_daemon:
# Run the daemon in a separate thread, the daemon will execute the daemon_task
# function every interval seconds, the main thread can continue to do other things,
# and the daemon will keep running in the background
def run_daemon(interval=1):
    """Run a daemon that executes every interval seconds"""
    def worker():
        while True:
            if not gen.daemon_pause:
                daemon_task()
                time.sleep(interval)
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()


# ================================================================
# Agent tool calls
# ================================================================
# tool_handle_task
# execute the command from grok when the command is "tasks", the command format should be:
# tasks update task_name content_in_xml_format
# tasks delete task_name
# tasks list
# tasks info task_name
def tool_handle_task(command):
    """Execute the command from grok when the command is tasks, the command format should be:
      update task_name content_in_xml_format
      delete task_name
      list
      info task_name"""
    parts = command.split(' ', 2)
    subcommand = parts[0]
    if subcommand == "update":
        if len(parts) != 3:
            return "ERROR: Invalid command format for update, number of arguments must be 3."
        task_name = parts[1]
        content = parts[2]
        return update_task(task_name, content)
    elif subcommand == "delete":
        if len(parts) != 2:
            return "ERROR: Invalid command format for delete, number of arguments must be 2."
        task_name = parts[1]
        return delete_task(task_name)
    elif subcommand == "list":
        if len(parts) != 1:
            return "ERROR: Invalid command format for list, number of arguments must be 1."
        tasks = list_tasks()
        result = ""
        for name, content in tasks.items():
            result += f"Task Name: {name}\nContent:\n{content}\n\n"
        return result.strip()
    elif subcommand == "info":
        if len(parts) != 2:
            return "ERROR: Invalid command format for info, number of arguments must be 2."
        task_name = parts[1]
        return get_task_info(task_name)
    else:
        return "ERROR: Unknown subcommand."

def tool_register():
    run_daemon()
    return {
        "name": "task",
        "description": "Manage scheduled tasks with XML-defined actions and looping behavior.",
        "handler": tool_handle_task,
        "definition": tool_define_task,
        "prompt": {
            "brief": tool_brief_task,
            "rule": tool_rule_task
        }
    }

# ================================================================
# Verification of tool calls
# ================================================================
# tool_tasks_validate
# inject all valid or invalid commands to function execute_tasks_command
def tool_tasks_validate():
    def test_update():
        valid_command = "update test_task <?xml version='1.0' encoding='utf-8'?>"
        valid_command += "<task><countdown>60</countdown><action>echo 'Hello, World!'</action>"
        valid_command += "<loop><enable>1</enable><interval>60</interval><remain>5</remain></loop></task>"
        invalid_command = "update test_task invalid_xml"
        print("Testing valid update command:")
        print(tool_handle_task(valid_command))
        print("\nTesting invalid update command:")
        print(tool_handle_task(invalid_command))

    def test_delete():
        valid_command = "delete test_task"
        invalid_command = "delete non_existent_task"
        print("Testing valid delete command:")
        print(tool_handle_task(valid_command))
        print("\nTesting invalid delete command:")
        print(tool_handle_task(invalid_command))
    
    def test_list():
        command = "list"
        print("Testing list command:")
        print(tool_handle_task(command))

    def test_info():
        valid_command = "info test_task"
        invalid_command = "info non_existent_task"
        print("Testing valid info command:")
        print(tool_handle_task(valid_command))
        print("\nTesting invalid info command:")
        print(tool_handle_task(invalid_command))
    
    print("Verifying update command:")
    test_update()
    print("\nVerifying list command:")
    test_list()
    print("\nVerifying info command:")
    test_info()
    print("\nVerifying delete command:")
    test_delete()
    print("\nVerification completed.")

if __name__ == "__main__":
    tool_tasks_validate()
