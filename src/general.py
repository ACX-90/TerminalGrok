"""
General utilities and shared state for the project.

This module centralizes lightweight global variables and helper functions
used across the CLI, daemon, and tool-invocation logic.

Globals exposed here act as simple process-wide flags and stores:
pause toggles for background tasks, an initial-entry marker, a flag
indicating whether a tool was used last, and a short place to keep
recent tool results for logging or returning to callers.

Utility functions provide basic XML <-> dict conversion:
- xml_to_dict(xml_file): parse an XML file into a nested dictionary,
    preserving element attributes and text under dedicated keys.
- dict_to_xml(data, output_file): build and write pretty-printed XML
    from the dictionary form.

Design notes:
- These globals are intentionally simple; protect with threading locks or
    encapsulate in an object if concurrent access is required.
- Keep helpers minimal to avoid extra dependencies and simplify testing.
"""
import os
import xml.etree.ElementTree as ET
import global_cfg as glb

# pause flag for the daemon, when daemon_pause is 1, the daemon will pause and not execute the
# tasks, when daemon_pause is 0, the daemon will run normally.
# need to run daemon before grok get user input, so that the daemon can execute the tasks in
# the background while grok is waiting for user input.
# when grok is processing user input or executing tools, it can set daemon_pause to 1 to pause
# the daemon, to avoid the daemon execute tasks at the same time and cause conflicts
daemon_pause = 0
# initial switch, to print welcome info and set default conversation at the first entry
initial = 0
# a flag to indicate whether the agent used tool last time, 
# if yes, the agent will not ask for user input, but directly decide to use tools or not once 
# again, which can be useful when the agent need to use tools for several times in a row
tool_used_last_time = 0
# a variable to store the tool result, which can be used for debugging and also can be sent back
# to grok as tool call reply content
tool_result = ""

# xml_to_dict:
# convert xml file to dictionary, the xml file should have a root element, and the root element
# can have multiple child elements, the child elements can also have their own child elements, 
# and so on, the function will recursively convert the xml file to a nested dictionary, the 
# attributes of the elements will be stored in a special key "@attributes", and the text content
# of the elements will be stored in a special key "#text"
def xml_to_dict(xml_file):
    def _element_to_dict(element):
        """Recursively convert XML element to dictionary"""
        result = {}
        if element.attrib:
            result['@attributes'] = element.attrib
        for child in element:
            child_dict = _element_to_dict(child)
            if child.tag in result:
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_dict)
            else:
                result[child.tag] = child_dict
        if element.text and element.text.strip():
            result['#text'] = element.text.strip()
        return result if result else None
    """Convert XML file to dictionary"""
    tree = ET.parse(xml_file)
    root = tree.getroot()
    return {root.tag: _element_to_dict(root)}

# dict_to_xml:
# convert dictionary to xml file, the dictionary should have a root key, and the value of the
# root key is a dictionary that represents the child elements of the root element, the function
# will recursively convert the dictionary to an xml file,
# the attributes of the elements should be stored in a special key "@attributes", and the text
# content of the elements should be stored in a special key "#text", the function will also add
# pretty-print indentation to the xml file for better readability
def dict_to_xml(data, output_file):
    """Convert dictionary to XML file"""
    def _dict_to_element(tag, data):
        """Recursively convert dictionary to XML element"""
        element = ET.Element(tag)
        if isinstance(data, dict):
            if '@attributes' in data:
                element.attrib.update(data['@attributes'])
            for key, value in data.items():
                if key == '@attributes' or key == '#text':
                    continue
                if isinstance(value, list):
                    for item in value:
                        element.append(_dict_to_element(key, item))
                else:
                    element.append(_dict_to_element(key, value))
            if '#text' in data:
                element.text = data['#text']
        else:
            element.text = str(data)
        return element
    
    def _indent(elem, level=0):
        """Add pretty-print indentation to XML"""
        indent = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = indent + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = indent
            for child in elem:
                _indent(child, level + 1)
            if not child.tail or not child.tail.strip():
                child.tail = indent
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = indent
    
    root_tag = list(data.keys())[0]
    root = _dict_to_element(root_tag, data[root_tag])
    _indent(root)
    tree = ET.ElementTree(root)
    tree.write(output_file, encoding='utf-8', xml_declaration=True)

# get_cfg:
# get configuration from cfg file, the cfg file should be in the format of "key=value", 
# and the key can be in the format of "tag_subtag", which will be converted to a nested dictionary,
# the value can be an integer, a string, a reference to another configuration value in the format
# of "${tag_subtag}", or a file path, if the value is a file path, the function will read the content
# of the file and return it as the value
def get_cfg(name: str) -> dict:
    def _resolve_value(value: str, cfg: dict) -> int | str:
        try:
            return int(value)
        except ValueError:
            pass
        # resolve references in the value, the reference format is "${tag_subtag}"
        # the reference can refer to an environment variable or another configuration value that has been parsed,
        # and the function will recursively resolve the references until there is no reference in the value
        while True:
            index_start = value.find("${")
            index_end = value.find("}")
            if index_start == -1 or index_end == -1:
                break
            ref = value[index_start + 2:index_end]
            ref_value = os.getenv(ref)
            if ref_value is None:
                # try to get the value from the already parsed cfg
                ref_parts = ref.split('_')
                ref_value = cfg
                for part in ref_parts:
                    if part in ref_value:
                        ref_value = ref_value[part]
                    else:
                        raise ValueError(f"Reference {ref} not found in environment variables or config")
            value = value[:index_start] + str(ref_value) + value[index_end + 1:]
        if os.path.isfile(value):
            with open(value, 'r') as f:
                return f.read()
        return value
    
    cfg = {}
    with open(f"{glb.config_dir}{glb.path_sep}{name}.cfg", 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith(';'):
                continue
            if '=' not in line:
                continue
            tag, _, raw_value = line.partition('=')
            value = _resolve_value(raw_value, cfg)
            if '_' in tag:
                tag, subtag = tag.split('_', 1)
                cfg.setdefault(tag, {})[subtag] = value
            else:
                cfg[tag] = value
    return cfg
