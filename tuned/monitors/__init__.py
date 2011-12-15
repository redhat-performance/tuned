import base
import repository

def get_repository():
	return repository.MonitorRepository.get_instance()

Monitor = base.Monitor
