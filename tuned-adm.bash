# bash completion for tuned-adm

_tuned-adm_get-profiles()
{
    local config_file='/etc/tuned/tuned-main.conf'
    local curV="$(tuned --version)"  # Convert to lowercase to be safe (below)
    local minV='tuned 2.23.0'
    local versions="$minV"$'\n'"${curV,,?}"
    local profile_dirs  # Default value

    # (GNU version of `sort` is needed for this)
    if [[ "$versions" != "$(sort --version-sort <<<"$versions")" ]]; then
        profile_dirs='/usr/lib/tuned,/etc/tuned'
    else
        profile_dirs='/usr/lib/tuned/profiles,/etc/tuned/profiles'

        # Find `profile_dirs` definition (only supported >=v2.23.0)
        if [[ -f "$config_file" ]] && [[ -r "$config_file" ]]; then
            parsed_dirs="$(grep -E '^profile_dirs\s*=\s*.*$' "$config_file")"

            [[ -n "$parsed_dirs" ]] &&
                profile_dirs="$(sed -En 's/profile_dirs\s*=\s*(.*)$/\1/p' <<<"${parsed_dirs##*$'\n'}")"
        fi
    fi

    # Print list of profiles
    local IFS=',;'
    [[ -n "$profile_dirs" ]] &&
        find $profile_dirs -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null
    return 0
}


_tuned_adm()
{
	local commands="active list off profile recommend verify --version -v --help -h auto_profile profile_mode profile_info"
	local cur prev words cword
	_init_completion || return

	if [[ "$cword" -eq 1 ]]; then
		COMPREPLY=( $(compgen -W "$commands" -- "$cur") )
	elif [[ "$cword" -eq 2 && ("$prev" == "profile" || "$prev" == "profile_info") ]]; then
        COMPREPLY=( $(compgen -W "$(_tuned-adm_get-profiles)" -- "$cur") )
	else
		COMPREPLY=()
	fi

	return 0
} &&
complete -F _tuned_adm tuned-adm
