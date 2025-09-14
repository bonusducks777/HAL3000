#!/bin/bash

set -eu

EXECUTABLE=(sh -c "echo 'n' | maestro studio --no-window")

# List of exception patterns (regex)
EXCEPTIONS=(
  'Exception in thread "pool-4-thread-1" java.io.IOException:'
)

function wait_for_device() {
    if [ ! -z "${ADB_CONNECT_ADDR:-}" ]; then
        while true; do
            set +e
            adb connect "$ADB_CONNECT_ADDR"
            state="$(adb get-state 2>/dev/null)"
            set -e

            if [[ "$state" = "device" ]]; then
                echo "Device is connected and authorized!"
                break
            fi

            echo "Waiting for device authorization... (accept the prompt on your phone)"
            set +e; adb disconnect "$ADB_CONNECT_ADDR"; set -e
            sleep 2
        done
    fi

    echo "Waiting for device to be connected..."
    adb wait-for-device

    echo "Waiting for device to be ready for commands..."
    while [ "$(adb shell getprop sys.boot_completed 2>/dev/null)" != "1" ]; do
        sleep 1
    done

    echo "Device is fully booted and ready!"
}

# Function to check if a line matches any exception pattern
function is_exception() {
    local line="$1"
    for pattern in "${EXCEPTIONS[@]}"; do
        if [[ "$line" =~ $pattern ]]; then
            return 0
        fi
    done
    return 1
}

while true; do
    adb start-server

    wait_for_device

    "${EXECUTABLE[@]}" 2>&1 | while IFS= read -r line; do
        echo "$line"
    
        if is_exception "$line"; then
            echo "Exception detected: $line"
            pids=$(pgrep -f "maestro")
            if [[ -n "$pids" ]]; then
                echo "Killing process(es): $pids"
                kill $pids
            fi
      
        break
        fi
    done

    echo "Restarting maestro..."
    adb kill-server
    sleep 1
done
