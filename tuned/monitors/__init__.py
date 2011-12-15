import base
import repository

__all__ = ["get_repository", "Monitor"]

def get_repository():
	return repository.MonitorRepository.get_instance()

Monitor = base.Monitor
