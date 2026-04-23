#!/bin/sh
set -u

SCRIPT_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$SCRIPT_DIR" || exit 1

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "Python was not found."
    echo "Please install Python and try again."
    printf "Press Enter to close..."
    read _unused
    exit 1
fi

"$PYTHON" main.py
EXIT_CODE=$?

echo
if [ "$EXIT_CODE" -eq 0 ]; then
    echo "Run completed. Please check the logs folder for details."
else
    echo "Run failed. Please check the message above and the logs folder."
fi

printf "Press Enter to close..."
read _unused
exit "$EXIT_CODE"
