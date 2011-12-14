import interface
import repository

def get_repository():
	return repository.PluginRepository.get_instance()
