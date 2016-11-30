# rebuilder bash completion

_rebuilder()
{
    in_array()
    {
        local i
        for i in $2; do
            [[ "$i" = "$1" ]] && return 0
        done
        return 1
    }

    local cur=${COMP_WORDS[COMP_CWORD]}
    local prev=${COMP_WORDS[COMP_CWORD - 1]}

    local commands="mock build scratch"
    local completions=""
    local branches=$(_rebuilder_branch)

    case "$prev" in
        "rebuilder")
            COMPREPLY=( $(compgen -W "$commands --no-rebase" -- "$cur") )
            return 0
            ;;
        "scratch")
            completions="--srpm"
            ;;
    esac


    if in_array "$prev" "$commands --srpm"; then
        completions="$completions $branches"
    elif in_array "$prev" "$branches"; then
        completions="$completions $branches"
    else
        completions="$completions $commands"
    fi

    COMPREPLY=( $(compgen -W "$completions" -- "$cur") )
} &&
complete -F _rebuilder rebuilder

_rebuilder_branch()
{
    git for-each-ref --format "%(refname:short)" "refs/heads"
}
