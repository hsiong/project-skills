#!/bin/bash

set -euo pipefail

TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
REPO="${1:-${GITHUB_REPOSITORY:-}}"
ISSUE_DIR="${2:-docs/issue}"

if [ -z "$TOKEN" ]; then
    echo "error: set GITHUB_TOKEN or GH_TOKEN before submitting issues"
    exit 1
fi

if ! command -v jq > /dev/null 2>&1; then
    echo "error: jq is required"
    exit 1
fi

if [ -z "$REPO" ]; then
    ORIGIN_URL="$(git config --get remote.origin.url || true)"
    REPO="$(printf '%s\n' "$ORIGIN_URL" \
        | sed -E 's#^git@github.com:##; s#^https://github.com/##; s#\.git$##')"
fi

if ! printf '%s' "$REPO" | grep -Eq '^[^/]+/[^/]+$'; then
    echo "error: repository must be owner/repo"
    echo "usage: $0 owner/repo [issue_dir]"
    exit 1
fi

if [ ! -d "$ISSUE_DIR" ]; then
    echo "error: issue directory not found: $ISSUE_DIR"
    exit 1
fi

API_URL="https://api.github.com/repos/$REPO/issues"
FOUND=0

for file in "$ISSUE_DIR"/*.md; do
    if [ ! -f "$file" ]; then
        break
    fi

    FOUND=1
    TITLE="$(sed -n '1{/^#/ {s/^# *//; p;}}' "$file")"
    BODY="$(sed '1{/^# */d;}; 1{/^$/d;}' "$file")"

    if [ -z "$TITLE" ]; then
        TITLE="$(basename "$file" .md | tr '-' ' ')"
    fi

    JSON_PAYLOAD="$(jq -n \
        --arg title "$TITLE" \
        --arg body "$BODY" \
        '{title: $title, body: $body}')"

    RESPONSE="$(curl -sS -w '\n%{http_code}' -X POST "$API_URL" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Accept: application/vnd.github.v3+json" \
        -H "X-GitHub-Api-Version: 2022-11-28" \
        -d "$JSON_PAYLOAD")"

    HTTP_CODE="$(printf '%s\n' "$RESPONSE" | tail -n 1)"
    BODY_RESP="$(printf '%s\n' "$RESPONSE" | sed '$d')"

    if [ "$HTTP_CODE" = "201" ]; then
        ISSUE_URL="$(printf '%s\n' "$BODY_RESP" | jq -r .html_url)"
        echo "created: $TITLE"
        echo "$ISSUE_URL"
    else
        MESSAGE="$(printf '%s\n' "$BODY_RESP" | jq -r .message 2>/dev/null || printf '%s\n' "$BODY_RESP")"
        echo "failed: $TITLE"
        echo "http_status: $HTTP_CODE"
        echo "message: $MESSAGE"
        exit 1
    fi

    sleep 1
done

if [ "$FOUND" -eq 0 ]; then
    echo "error: no markdown issue files found in $ISSUE_DIR"
    exit 1
fi
