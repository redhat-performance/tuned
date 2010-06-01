# bash completion for tuned and tuned-adm

_tuned()
{
	local options="-d --daemon -c --config -D --debug"
	local current="${COMP_WORDS[$COMP_CWORD]}"
	local previous="${COMP_WORDS[$COMP_CWORD-1]}"

	if [[ "$previous" == "-c" || "$previous" == "--config" ]]; then
		COMPREPLY=( $(compgen -f -- "$current") )
	else
		COMPREPLY=( $(compgen -W "$options" -- "$current") )
	fi

	return 0
} &&
complete -F _tuned -o filenames tuned

_tuned_adm()
{
	local commands="help list active off profile"
	local current="${COMP_WORDS[$COMP_CWORD]}"
	local previous="${COMP_WORDS[$COMP_CWORD-1]}"

	if [[ $COMP_CWORD -eq 1 ]]; then
		COMPREPLY=( $(compgen -W "$commands" -- "$current" ) )
	elif [[ $COMP_CWORD -eq 2 && "$previous" == "profile" ]]; then
		COMPREPLY=( $(compgen -W "$(command ls -F /etc/tune-profiles | \
			sed '/\/$/!d;s/.$//')" -- "$current" ) )
	else
		COMPREPLY=()
	fi

	return 0
} &&
complete -F _tuned_adm tuned-adm

# Local variables:
# mode: shell-script
# sh-basic-offset: 4
# sh-indent-comment: t
# indent-tabs-mode: nil
# End:
# ex: ts=4 sw=4 et filetype=sh
