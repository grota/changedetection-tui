#!/bin/bash

# Fetch latest from origin to ensure we have up-to-date remote refs
git fetch origin main

# Get commit hashes
local_head=$(git rev-parse HEAD)
origin_head=$(git rev-parse origin/main)

# Compare commits
if [ "$local_head" = "$origin_head" ]; then
    echo "Main branch is up to date with origin/main"
    exit 0
else
    echo "Main branch is NOT up to date with origin/main"
    echo "Local HEAD:  $local_head"
    echo "Origin HEAD: $origin_head"
    exit 1
fi