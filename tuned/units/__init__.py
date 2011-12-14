__all__ = ["manager", "unit"]

import manager
import unit

def get_manager():
	return manager.UnitManager.get_instance()
