#compdef tuned

_tuned_get-profiles()
{
    local config_file='/etc/tuned/tuned-main.conf'
    local curV="${(L)$(tuned --version)}"  # Convert to lowercase to be safe
    local minV='tuned 2.23.0'
    local versions="$minV"$'\n'"$curV"
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
    find "${=profile_dirs}" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null
    return 0
}


_tuned()
{
    # local variables needed by _arguments
    local context state state_descr line
    typeset -A opt_args

    local -a global_args=('(-d --daemon)'{-d,--daemon}'[run in background]'
                          '(-D --debug)'{-D,--debug}'[show/log debugging messages]'
                          '(-l --log)'{-l,--log}'[use log file]::path:_files'
                          '(-P --pid)'{-P,--pid}'[use PID file]::path:_files'
                          '(-p --profile)'{-p+,--profile=}'[tuning profile to be activated]:profile:->profile'
                          '(- :)'{-h,--help}'[show help message and exit]'
                          '(- :)'{-v,--version}'[show program'\''s version number and exit]'
                          '--no-dbus[do not attach to Dbus]'
                          '--no-socket[do not attach to socket]')

    # The lack of a delimiter for path options is intentional -- if a filepath
    # is adjacent to an equals sign, then tilde expansion will not occur

    _arguments -s -S "${global_args[@]}" && return 0

    case "$state" in
        (profile) _values 'profile' "${(f)$(_tuned_get-profiles)}" ;;
    esac

    return 0
}
