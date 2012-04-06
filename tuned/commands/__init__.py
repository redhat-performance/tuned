import base
import repository

__all__ = ["repository", "get_repository", "Command"]

def get_repository():
	return repository.CommandRepository.get_instance()

Command = base.Command
