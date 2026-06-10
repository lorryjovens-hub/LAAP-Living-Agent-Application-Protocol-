"""Plugin management"""
def run(args):
    from laap.agent_core.plugins.manager import PluginManager
    pm = PluginManager()
    if getattr(args, 'action', 'list') == "list":
        infos = pm.discover()
        print(f"\nPlugins: {len(infos)} found")
        for info in infos:
            print(f"  {info.name}: {info.description}")
