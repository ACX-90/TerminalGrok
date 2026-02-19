import os
import sys
import re

# ================================================================
# Basic file operations
# ================================================================
# path_preprocess
# preprocess path to make sure it's safe and valid
def path_preprocess(path):
    """Sometimes path may contail \" in the start and end """
    if path.startswith('"') and path.endswith('"'):
        path = path[1:-1]
    return path

# data_preprocess
# unescape data to make sure it's safe and valid, 
# for example, replace \\n with \n, \\t with \t and \\\\ with \\
def data_preprocess(text):
    def replace(m):
        s = m.group(0)
        escape_map = {
            '\\\\': '\\',
            '\\n': '\n',
            '\\t': '\t',
            '\\r': '\r',
        }
        return escape_map.get(s, s)
    if text.startswith('"') and text.endswith('"'):
        text = text[1:-1]
    return re.sub(r'\\(\\|n|t|r)', replace, text)

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


# ================================================================
# Verification of tool calls
# ================================================================


