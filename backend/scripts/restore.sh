#!/bin/sh
set -eu

if [ -z "${TOKEN:-}" ]; then
  echo "TOKEN environment variable is required"
  exit 1
fi

if [ -z "${BACKUP_ID:-}" ]; then
  echo "BACKUP_ID environment variable is required"
  exit 1
fi

API_BASE="${API_BASE:-http://localhost:8810}"

curl -sS -X POST "${API_BASE}/api/admin/backups/${BACKUP_ID}/restore" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json"
