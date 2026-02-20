"""
This module implements a daemon system for task scheduling and execution.
It provides functionality to periodically check for task files in a specified directory,
execute tasks based on their XML-defined parameters, and handle recurring tasks with loops.
The daemon runs in a background thread, allowing the main program to continue other operations.

Function that runs periodically to check and execute tasks from .task files in the task directory.
This function iterates through all .task files in the taskdir directory. For each file:
- Loads the task data from XML format.
- If the task has a 'countdown', converts it to a 'start_time' based on current time.
- If the current time has reached the 'start_time', executes the task action.
- Handles looping tasks by updating the start_time and remaining loop count, or deletes the file
    if no loops remain.
- For non-looping tasks, deletes the file after execution.
The task execution involves printing the action (and presumably sending it to a communication
channel).

Run a daemon that executes the daemon_task function every specified interval seconds in a
background thread.
This function creates and starts a daemon thread that runs an infinite loop, calling daemon_task()
at regular intervals (default 1 second), unless the daemon is paused via the global daemon_pause
flag.
The main thread can continue executing other code while the daemon runs in the background.
Args:
        interval (int or float, optional): The time in seconds between daemon_task executions.
                Defaults to 1.
Returns:
        threading.Thread: The daemon thread object that was started.
"""
import threading
import time
import os
import agent
from datetime import datetime
from global_cfg import *
from generic import *

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
    dict_to_xml(load_task, task_path)

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
        with open(agent.grok_fcomm_in_task, "w") as f:  # assuming 'agent' is available in scope
            f.write(f"Scheduled Task {exec_info}:\n{action_text}\n<GROK status=start></GROK>")
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
    dict_to_xml(load_task, task_path)  # assuming this function exists and works correctly
    next_exec_time = datetime.fromtimestamp(current_task['start_time'])
    remaining_display = "infinite" if remain == -1 else str(remain)
    print(f"Task {taskfile} executed. Next run at {next_exec_time}, "
          f"remaining executions: {remaining_display}")

# daemon_task:
# Function that runs periodically, checks taskdir for .task files and executes them
def daemon_task():
    """Function that runs periodically, checks taskdir for .task files and executes them"""
    for taskfile in os.listdir(taskdir):
        if not (isinstance(taskfile, str) and taskfile.endswith('.task')):
            continue
        task_path = os.path.join(taskdir, taskfile)
        load_task = xml_to_dict(task_path)
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
            if not daemon_pause:
                daemon_task()
                time.sleep(interval)
    
    thread = threading.Thread(target=worker, daemon=True)
    thread.start()
    return thread
