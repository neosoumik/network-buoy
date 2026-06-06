#!/bin/sh
set -e

MODEL="${OLLAMA_MODEL:-gemma3:1b}"

# Start ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait until ollama is accepting requests
echo "Waiting for ollama to start..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama ready."

# Pull model if not already cached
if ! ollama list | grep -q "^${MODEL}"; then
    echo "Pulling ${MODEL}..."
    ollama pull "${MODEL}"
fi

echo "Starting network-buoy..."
exec uv run main.py
