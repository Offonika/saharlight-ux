#!/bin/bash
set -e

# Create required directories
mkdir -p services/api services/bot libs infra docs/ADR

# Add .gitkeep files for empty directories
: > services/bot/.gitkeep
: > libs/.gitkeep
: > infra/.gitkeep
: > docs/ADR/.gitkeep

# Move webapp into services if it exists at the repository root
if [ -d webapp ]; then
    mv webapp services/webapp
fi
