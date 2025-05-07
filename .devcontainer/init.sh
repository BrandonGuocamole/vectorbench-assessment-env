#!/usr/bin/env bash
set -e

echo "Setting up VectorBench assessment environment..."

# Install pytest via pipx for better isolation
echo "Installing pytest..."
pipx install pytest==8.*

# Install system dependencies (entr for file watching, zip for submission)
echo "Installing system dependencies..."
apt-get update
apt-get install entr zip -y

# Copy watch.sh to /usr/local/bin to make it executable from anywhere
echo "Setting up test auto-runner..."
cp .devcontainer/watch.sh /usr/local/bin/
chmod +x /usr/local/bin/watch.sh

# Start the test auto-runner in the background
echo "Starting test auto-runner in background..."
nohup bash /usr/local/bin/watch.sh &

echo "Environment setup complete!" 