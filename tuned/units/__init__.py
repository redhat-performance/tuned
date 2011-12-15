import manager

__all__ = ["manager", "get_manager"]

def get_manager():
	return manager.UnitManager.get_instance()
