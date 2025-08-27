#!/bin/bash
set -e

# Create required directories
mkdir -p services/api services/bot libs infra docs/ADR

# Add .gitkeep files for empty directories
: > services/bot/.gitkeep
: > libs/.gitkeep
: > infra/.gitkeep
: > docs/ADR/.gitkeep
