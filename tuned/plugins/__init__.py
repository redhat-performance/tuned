import base
import repository

def get_repository():
	return repository.PluginRepository.get_instance()

Plugin = base.Plugin
