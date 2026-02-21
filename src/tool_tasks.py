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
import os
import sys
import time
from global_cfg import *
from general import *
import xml.etree.ElementTree as ET

# =================================================================
# Tool tasks management
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
    task_path = f"{taskdir}/{task_name}.task"
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
    task_path = os.path.join(taskdir, f"{task_name}.task")
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
    for file in os.listdir(taskdir):
        if isinstance(file, str) and file.endswith('.task'):
            task_name = file[:-5]  # remove .task extension
            task_path = os.path.join(taskdir, file)
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
    task_path = os.path.join(taskdir, f"{task_name}.task")
    if not os.path.exists(task_path):
        return "ERROR: Task does not exist."
    try:
        with open(task_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        return f"ERROR: Failed to read task. {str(e)}"

# ================================================================
# Agent tool calls
# ================================================================
# execute_tasks_command
# execute the command from grok when the command is "tasks", the command format should be:
# tasks update task_name content_in_xml_format
# tasks delete task_name
# tasks list
# tasks info task_name
def execute_tasks_command(command):
    """Execute the command from grok when the command is tasks, the command format should be:
      update task_name content_in_xml_format
      delete task_name
      list
      info task_name"""
    parts = command.split(' ', 2)
    subcommand = parts[0]
    if subcommand == "update":
        if len(parts) != 3:
            return "ERROR: Invalid command format for update."
        task_name = parts[1]
        content = parts[2]
        return update_task(task_name, content)
    elif subcommand == "delete":
        if len(parts) != 2:
            return "ERROR: Invalid command format for delete."
        task_name = parts[1]
        return delete_task(task_name)
    elif subcommand == "list":
        if len(parts) != 1:
            return "ERROR: Invalid command format for list."
        tasks = list_tasks()
        result = ""
        for name, content in tasks.items():
            result += f"Task Name: {name}\nContent:\n{content}\n\n"
        return result.strip()
    elif subcommand == "info":
        if len(parts) != 2:
            return "ERROR: Invalid command format for info."
        task_name = parts[1]
        return get_task_info(task_name)
    else:
        return "ERROR: Unknown subcommand."
    
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
        print(execute_tasks_command(valid_command))
        print("\nTesting invalid update command:")
        print(execute_tasks_command(invalid_command))

    def test_delete():
        valid_command = "delete test_task"
        invalid_command = "delete non_existent_task"
        print("Testing valid delete command:")
        print(execute_tasks_command(valid_command))
        print("\nTesting invalid delete command:")
        print(execute_tasks_command(invalid_command))
    
    def test_list():
        command = "list"
        print("Testing list command:")
        print(execute_tasks_command(command))

    def test_info():
        valid_command = "info test_task"
        invalid_command = "info non_existent_task"
        print("Testing valid info command:")
        print(execute_tasks_command(valid_command))
        print("\nTesting invalid info command:")
        print(execute_tasks_command(invalid_command))
    
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
