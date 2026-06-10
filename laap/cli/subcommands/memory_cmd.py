"""Memory management"""
def run(args):
    from laap.agent_core.memory_manager import MemoryManager
    mm = MemoryManager()
    stats = mm.get_stats()
    print(f"Memory: {stats}")
