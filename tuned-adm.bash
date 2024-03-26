# bash completion for tuned-adm

_tuned_adm()
{
	local commands="active list off profile recommend verify --version -v --help -h auto_profile profile_mode profile_info"
	local cur prev words cword
	_init_completion || return

	if [[ "$cword" -eq 1 ]]; then
		COMPREPLY=( $(compgen -W "$commands" -- "$cur" ) )
	elif [[ "$cword" -eq 2 && ("$prev" == "profile" || "$prev" == "profile_info") ]]; then
		COMPREPLY=( $(compgen -W "$(command find /usr/lib/tuned/profiles /etc/tuned/profiles -mindepth 1 -maxdepth 1 -type d -printf "%f\n")" -- "$cur" ) )
	else
		COMPREPLY=()
	fi

	return 0
} &&
complete -F _tuned_adm tuned-adm
