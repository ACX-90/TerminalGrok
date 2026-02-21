"""
Module for basic file I/O operations and content manipulations.
Provides functions for file operations like read, write, append, delete, and content manipulation.
Includes path and data preprocessing to handle quotes and escape sequences safely.
Functions return success or error messages for easy integration with agents or scripts.
Key functions:
- path_preprocess: Strips surrounding quotes from paths.
- data_preprocess: Unescapes common escape sequences in text data.
- file_write: Writes data to a file, creating directories if needed.
- file_read: Reads and returns file content.
- file_append: Appends data to a file.
- file_delete: Deletes a file if it exists.
- file_insert_lines: Inserts lines before a specified line number.
- file_delete_lines: Deletes a range of lines.
- file_replace_lines: Replaces lines with new data.
- file_replace_symbol: Replaces all occurrences of a symbol in the file.
- execute_fileio_command: Parses and executes file I/O commands from agents.
"""

import os
import sys
import re

# ================================================================
# Basic file operations
# ================================================================
# path_preprocess
# preprocess path to make sure it's safe and valid
def path_preprocess(path):
    """Sometimes path may contain \" in the start and end """
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path

# data_preprocess
# unescape data to make sure it's safe and valid, 
# for example, replace \\n with \n, \\t with \t and \\\\ with \\
def data_preprocess(text):
    escape_map = {
        '\\\\': '\\',
        '\\n':  '\n',
        '\\r':  '\r',
        '\\t':  '\t',
        '\\v':  '\v',
        '\\a':  '\a',
        '\\b':  '\b',
        '\\f':  '\f',
        '\\/':  '/',
        '\\"':  '"',
        "\\'":  "'",
        '\\0':  '\0',
    }
    def replace(m):
        s = m.group(0)
        # oct \012
        if re.match(r'\\[0-7]{1,3}', s):
            return chr(int(s[1:], 8))
        # hex \xFF
        if re.match(r'\\x[0-9a-fA-F]{2}', s):
            return chr(int(s[2:], 16))
        # Unicode \uFFFF
        if re.match(r'\\u[0-9a-fA-F]{4}', s):
            return chr(int(s[2:], 16))
        # Unicode \UFFFFFFFF
        if re.match(r'\\U[0-9a-fA-F]{8}', s):
            return chr(int(s[2:], 16))
        return escape_map.get(s, s)  # unknown escape, return as is
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    pattern = r'\\(\\|n|r|t|v|a|b|f|/|"|\'|0|[0-7]{1,3}|x[0-9a-fA-F]{2}|u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8})'
    return re.sub(pattern, replace, text)

# file_write
# write data to a file, if the file does not exist, create it
def file_write(path, data):
    path = path_preprocess(path)
    data = data_preprocess(data)
    print(f"DEBUG: file_write called with path={path}, data={data}")
    """write data to a file, if the file does not exist, create it"""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    with open(path, 'w') as f:
        f.write(data)
    return "SUCCESS: file written."

# file_read
# read a file and return its content, if the file does not exist, return error
def file_read(path):
    path = path_preprocess(path)
    print(f"DEBUG: file_read called with path={path}")
    """read a file and return its content, if the file does not exist, return error"""
    if not os.path.isfile(path):
        return "ERROR: file not found."
    with open(path, 'r') as f:
        return f.read()

# file_append
# append data to a file, if the file does not exist, create it
def file_append(path, data):
    path = path_preprocess(path)
    data = data_preprocess(data)
    print("DEBUG: file_append called with path={path}, data={data}")
    """append data to a file, if the file does not exist, create it"""
    dir_name = os.path.dirname(path)
    if dir_name and not os.path.isdir(dir_name):
        os.makedirs(dir_name)
    with open(path, 'a') as f:
        f.write(data)
    return "SUCCESS: file appended."

# file_delete
# delete a file, if the file does not exist, return error
def file_delete(path):
    path = path_preprocess(path)
    print(f"DEBUG: file_delete called with path={path}")
    """delete a file, if the file does not exist, return error"""
    if os.path.isfile(path):
        os.remove(path)
        return "SUCCESS: File deleted."
    else:
        return "ERROR: file not found."

# ================================================================
# File content operations, line_num starts from 1
# ================================================================
# file_insert_lines
# insert multiple lines before line_num
def file_insert_lines(path, line_num, data):
    path = path_preprocess(path)
    data = data_preprocess(data)
    print(f"DEBUG: file_insert_lines called with path={path}, line_num={line_num}, data={data}")
    """insert multiple lines before line_num"""
    if not os.path.isfile(path):
        return "ERROR: file not found."
    with open(path, 'r') as f:
        lines = f.readlines()
    if not os.path.isfile(path + '.bak'):
        with open(path + '.bak', 'w') as f:
            f.writelines(lines)
    if line_num < 1 or line_num > len(lines) + 1:
        return "ERROR: line number out of range."
    data_list = data.split('\n')
    for i, item in enumerate(data_list):
        lines.insert(line_num - 1 + i, item + '\n')
    with open(path, 'w') as f:
        f.writelines(lines)
    return "SUCCESS: line inserted."

# file_delete_lines
# delete `count` lines starting from line_num
def file_delete_lines(path, line_num, count):
    path = path_preprocess(path)
    print(f"DEBUG: file_delete_lines called with path={path}, line_num={line_num}, count={count}")
    """delete `count` lines starting from line_num"""
    if not os.path.isfile(path):
        return "ERROR: file not found."
    with open(path, 'r') as f:
        lines = f.readlines()
    if not os.path.isfile(path + '.bak'):
        with open(path + '.bak', 'w') as f:
            f.writelines(lines)
    if line_num < 1 or line_num > len(lines):
        return "ERROR: line number out of range."
    if line_num + count - 1 > len(lines):
        return "ERROR: line number out of range."
    del lines[line_num - 1 : line_num - 1 + count]
    with open(path, 'w') as f:
        f.writelines(lines)
    return "SUCCESS: line deleted."

# file_replace_lines
# replace `count` lines starting from line_num with data_list
def file_replace_lines(path, line_num, count, data):
    path = path_preprocess(path)
    data = data_preprocess(data)
    print(f"DEBUG: file_replace_lines called with path={path}, line_num={line_num}, count={count}, data={data}")
    """replace `count` lines starting from line_num with data_list"""
    if not os.path.isfile(path):
        return "ERROR: file not found."
    with open(path, 'r') as f:
        lines = f.readlines()
    if not os.path.isfile(path + '.bak'):
        with open(path + '.bak', 'w') as f:
            f.writelines(lines)
    if line_num < 1 or line_num > len(lines):
        return "ERROR: line number out of range."
    if line_num + count - 1 > len(lines):
        return "ERROR: line number out of range."
    data_list = data.split('\n')
    del lines[line_num - 1 : line_num - 1 + count]
    for i, item in enumerate(data_list):
        lines.insert(line_num - 1 + i, item + '\n')
    with open(path, 'w') as f:
        f.writelines(lines)
    return "SUCCESS: line replaced."

# file_replace_symbol
# replace all occurrences of symbol in the file with data
# return error if file not found
# return error if symbol not found
def file_replace_symbol(path, symbol, data):
    path = path_preprocess(path)
    symbol = data_preprocess(symbol)
    data = data_preprocess(data)
    print(f"DEBUG: file_replace_symbol called with path={path}, symbol={symbol}, data={data}")
    """replace all occurrences of symbol in the file with data"""
    if not os.path.isfile(path):
        return "ERROR: file not found."
    with open(path, 'r') as f:
        content = f.read()
    if symbol not in content:
        return "ERROR: symbol not found."
    content = content.replace(symbol, data)
    with open(path, 'w') as f:
        f.write(content)
    return "SUCCESS: symbol replaced."

# ================================================================
# Agent tool calls
# ================================================================
# execute_fileio_command
# execute fileio command from agent, the command should follow the syntax defined in agent_cfg.py
def execute_fileio_command(agent_cmd):
    if agent_cmd.startswith("write "):
        args = agent_cmd[len("write "):].split(" ", 1)
        return file_write(args[0], args[1])
    elif agent_cmd.startswith("read "):
        args = agent_cmd[len("read "):].split(" ", 1)
        return file_read(args[0])
    elif agent_cmd.startswith("append "):
        args = agent_cmd[len("append "):].split(" ", 1)
        return file_append(args[0], args[1])
    elif agent_cmd.startswith("delete "):
        args = agent_cmd[len("delete "):].split(" ", 1)
        return file_delete(args[0])
    elif agent_cmd.startswith("insert_lines "):
        args = agent_cmd[len("insert_lines "):].split(" ", 2)
        return file_insert_lines(args[0], int(args[1]), args[2])
    elif agent_cmd.startswith("delete_lines "):
        args = agent_cmd[len("delete_lines "):].split(" ", 2)
        return file_delete_lines(args[0], int(args[1]), int(args[2]))
    elif agent_cmd.startswith("replace_lines "):
        args = agent_cmd[len("replace_lines "):].split(" ", 3)
        return file_replace_lines(args[0], int(args[1]), int(args[2]), args[3])
    elif agent_cmd.startswith("replace_symbol "):
        args = agent_cmd[len("replace_symbol "):].split(" ", 2)
        return file_replace_symbol(args[0], args[1], args[2])
    else:
        return f"ERROR: unknown fileio command."

# ================================================================
# Verification of tool calls
# ================================================================
# tool_fileio_validate
def tool_fileio_validate():
    def test_fileio_write():
        path = "test_file.txt"
        data = "Hello, World!"
        result = file_write(path, data)
        assert result == "SUCCESS: file written."
        assert os.path.isfile(path)
        with open(path, 'r') as f:
            content = f.read()
        assert content == data

    def test_fileio_read():
        path = "test_file.txt"
        data = "Hello, World!"
        with open(path, 'w') as f:
            f.write(data)
        result = file_read(path)
        assert result == data
    
    def test_fileio_append():
        path = "test_file.txt"
        data1 = "Hello"
        data2 = ", World!"
        with open(path, 'w') as f:
            f.write(data1)
        result = file_append(path, data2)
        assert result == "SUCCESS: file appended."
        with open(path, 'r') as f:
            content = f.read()
        assert content == data1 + data2
    
    def test_fileio_delete():
        path = "test_file.txt"
        with open(path, 'w') as f:
            f.write("Hello, World!")
        result = file_delete(path)
        assert result == "SUCCESS: File deleted."

    def test_fileio_insert_lines():
        path = "test_file.txt"
        with open(path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\n")
        result = file_insert_lines(path, 2, "Inserted Line 1\nInserted Line 2")
        assert result == "SUCCESS: line inserted."
        with open(path, 'r') as f:
            content = f.read()
        assert content == "Line 1\nInserted Line 1\nInserted Line 2\nLine 2\nLine 3\n"
    
    def test_fileio_delete_lines():
        path = "test_file.txt"
        with open(path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\n")
        result = file_delete_lines(path, 2, 2)
        assert result == "SUCCESS: line deleted."
        with open(path, 'r') as f:
            content = f.read()
        assert content == "Line 1\nLine 4\n"

    def test_fileio_replace_lines():
        path = "test_file.txt"
        with open(path, 'w') as f:
            f.write("Line 1\nLine 2\nLine 3\nLine 4\n")
        result = file_replace_lines(path, 2, 2, "Replaced Line 1\nReplaced Line 2")
        assert result == "SUCCESS: line replaced."
        with open(path, 'r') as f:
            content = f.read()
        assert content == "Line 1\nReplaced Line 1\nReplaced Line 2\nLine 4\n"

    def test_fileio_replace_symbol():
        path = "test_file.txt"
        with open(path, 'w') as f:
            f.write("Hello, World! Hello!")
        result = file_replace_symbol(path, "Hello", "Hi")
        assert result == "SUCCESS: symbol replaced."
        with open(path, 'r') as f:
            content = f.read()
        assert content == "Hi, World! Hi!"

    test_fileio_write()
    test_fileio_read()
    test_fileio_append()
    test_fileio_delete()
    test_fileio_insert_lines()
    test_fileio_delete_lines()
    test_fileio_replace_lines()
    test_fileio_replace_symbol()
    print("All file I/O tests passed.")

if __name__ == "__main__":
    tool_fileio_validate()
