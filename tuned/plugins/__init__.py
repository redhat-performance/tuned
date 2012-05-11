import base
import repository
import rfkill

__all__ = ["repository", "get_repository", "Plugin", "RFKillPlugin"]

def get_repository():
	return repository.PluginRepository.get_instance()

Plugin = base.Plugin
RFKillPlugin = rfkill.RFKillPlugin
