import interface
import repository

def get_repository():
	return repository.MonitorRepository.get_instance()
