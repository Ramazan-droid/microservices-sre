#!/bin/bash
set -e

echo "=== Pre-deployment Configuration Validation ==="

# Check .env exists
if [ ! -f ".env" ]; then
  echo "ERROR: .env file not found. Copy .env.example and fill in values."
  exit 1
fi

source .env

# Validate required variables
REQUIRED_VARS=("DATABASE_URL" "SECRET_KEY" "POSTGRES_USER" "POSTGRES_PASSWORD")
for VAR in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!VAR}" ]; then
    echo "ERROR: Required variable $VAR is missing from .env"
    exit 1
  fi
done

# Validate DATABASE_URL format
if [[ ! "$DATABASE_URL" =~ ^postgresql:// ]]; then
  echo "ERROR: DATABASE_URL must start with postgresql://"
  exit 1
fi

# Check for wrong-host (the Assignment 4 incident pattern)
if [[ "$DATABASE_URL" == *"wrong-host"* ]]; then
  echo "ERROR: DATABASE_URL contains 'wrong-host' — this caused the Assignment 4 incident!"
  exit 1
fi

echo "All configuration checks passed."
echo "=== Safe to deploy ==="