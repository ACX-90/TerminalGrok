import xml.etree.ElementTree as ET

# pause flag for the daemon, when daemon_pause is 1, the daemon will pause and not execute the
# tasks,
# when daemon_pause is 0, the daemon will run normally
# need to run daemon before grok get user input, so that the daemon can execute the tasks in the
# background
# while grok is waiting for user input
# when grok is processing user input or executing tools, it can set daemon_pause to 1 to pause
# the daemon,
# to avoid the daemon execute tasks at the same time and cause conflicts
daemon_pause = 0

# xml_to_dict:
# convert xml file to dictionary, the xml file should have a root element, and the root element
# can have multiple child
# elements, the child elements can also have their own child elements, and so on, the function
# will recursively convert
# the xml file to a nested dictionary, the attributes of the elements will be stored in a
# special key "@attributes",
# and the text content of the elements will be stored in a special key "#text"
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
# root key is a dictionary that
# represents the child elements of the root element, the function will recursively convert the
# dictionary to an xml file,
# the attributes of the elements should be stored in a special key "@attributes", and the text
# content of the elements should
# be stored in a special key "#text", the function will also add pretty-print indentation to the
# xml file for better readability
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
