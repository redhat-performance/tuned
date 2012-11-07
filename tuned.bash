# bash completion for tuned-adm

_tuned_adm()
{
	local commands="active list off profile"
	local current="${COMP_WORDS[$COMP_CWORD]}"
	local previous="${COMP_WORDS[$COMP_CWORD-1]}"

	if [[ $COMP_CWORD -eq 1 ]]; then
		COMPREPLY=( $(compgen -W "$commands" -- "$current" ) )
	elif [[ $COMP_CWORD -eq 2 && "$previous" == "profile" ]]; then
		COMPREPLY=( $(compgen -W "$(command find /usr/lib/tuned /etc/tuned -mindepth 1 -maxdepth 1 -type d -printf "%f\n")" -- "$current" ) )
	else
		COMPREPLY=()
	fi

	return 0
} &&
complete -F _tuned_adm tuned-adm
