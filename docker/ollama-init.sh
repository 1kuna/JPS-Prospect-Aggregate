#!/bin/bash
set -e

echo "Starting Ollama initialization..."

# Start Ollama server in background
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama server to start..."
while ! curl -s http://localhost:11434/api/version > /dev/null; do
    sleep 2
done

echo "Downloading qwen3:latest model..."
ollama pull qwen3:latest

echo "Ollama setup complete!"

# Keep Ollama server running
wait $OLLAMA_PID