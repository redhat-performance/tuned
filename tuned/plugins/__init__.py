from base import *
from rfkill import *
from decorator import *

import repository

__all__ = [
	"repository", "get_repository",
	"Plugin", "RFKillPlugin",
	"command_set", "command_get",
]

def get_repository():
	return repository.PluginRepository.get_instance()
