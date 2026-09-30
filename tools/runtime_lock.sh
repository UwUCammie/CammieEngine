#!/usr/bin/env bash
# Source this before Lime can copy files into the runtime directory. Keep FD 9
# open through exec so rebuilding cannot truncate a running game's mapped .ndll.
lock_runtime() {
    local lock_path="$1"
    exec 9>"$lock_path"
    if ! flock -n -x 9; then
        echo ">> waiting for the running game or build to finish..."
        flock -x 9
    fi
}
