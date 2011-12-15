import base
import repository

__all__ = ["repository", "get_repository", "Plugin"]

def get_repository():
	return repository.PluginRepository.get_instance()

Plugin = base.Plugin
