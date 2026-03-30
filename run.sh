#!/usr/bin/env bash
set -e

# Build if image doesn't exist or Dockerfile/pyproject changed
docker compose build --quiet

# Use 'run' instead of 'up' — properly attaches TTY for Textual TUI apps
exec docker compose run --rm dockmeister
