import importlib
import pkgutil
import sys
from pathlib import Path
import global_cfg as glb

tools = {}

def load_tools(tools_dir: str) -> dict:
    global tools
    tools = {}
    tools_path = Path(tools_dir)

    if str(tools_path.parent) not in sys.path:
        sys.path.insert(0, str(tools_path.parent))

    for finder, module_name, _ in pkgutil.iter_modules([str(tools_path)]):
        full_module_name = f"{tools_path.name}.{module_name}"
        # try:
        module = importlib.import_module(full_module_name)
        if hasattr(module, "tool_register"):
            info = module.tool_register()
            tools[info["name"]] = info
            print(f"✅ Load: Tool [{info['name']}] - {info['description']}")
        # except Exception as e:
        #     print(f"❌ Failed to load tool {module_name}: {e}")


def run_tool(tools: dict, name: str, args=None):
    """Run a tool by name"""
    if name not in tools:
        print(f"Tool '{name}' does not exist. Available tools: {list(tools.keys())}")
        return
    tools[name]["handler"](args)

def load_all_tools():
    load_tools(f"{glb.workspace}/src/tools")
    return

if __name__ == "__main__":
    load_all_tools()
    while True:
        pass