import importlib
import pkgutil
import sys
from pathlib import Path
import global_cfg as glb

"""
example for ai component structure:
components = {
    'openrouter': {
        'name': 'openrouter',
        'description': 'OpenRouter AI client',
        'chat': chat_function,
        'reset': reset_function,
        'init': init_function,
    },
    'xai': {
        'name': 'xai',
        'description': "xAI's API",
        'chat': chat_function,
        'reset': reset_function,
        'init': init_function,
    },
}
"""
components = {}

def load_components(components_dir: str) -> dict:
    global components
    components = {}
    components_path = Path(components_dir)

    if str(components_path.parent) not in sys.path:
        sys.path.insert(0, str(components_path.parent))

    for finder, module_name, _ in pkgutil.iter_modules([str(components_path)]):
        full_module_name = f"{components_path.name}.{module_name}"
        # try:
        module = importlib.import_module(full_module_name)
        if hasattr(module, "ai_register"):
            info = module.ai_register()
            components[info["name"]] = info
            print(f"✅ Load: AI [{info['name']}] - {info['description']}")
        # except Exception as e:
        #     print(f"❌ Failed to load component {module_name}: {e}")


def func(func: str, **kwargs):
    name = glb.ai_vendor
    """Run a component by name"""
    if name not in components:
        print(f"Component '{name}' does not exist. Available components: {list(components.keys())}")
        return
    if func not in components[name]:
        print(f"Function '{func}' does not exist in component '{name}'. Available functions: {list(components[name].keys())}")
        return
    return components[name][func](**kwargs)

def load_all_components():
    load_components(f"{glb.workspace}/src/ai")
    return

if __name__ == "__main__":
    load_all_components()
    while True:
        pass