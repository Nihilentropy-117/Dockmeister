#!/usr/bin/env bash
set -euo pipefail

# ─────────────────────────────────────────────────────────
# Rewrite entire git history:
#   - Replace "dockmanr" → "dockmeister" in file contents
#   - Replace "DockmanR" → "Dockmeister" in file contents
#   - Rename files and directories containing dockmanr/DockmanR
#   - Preserve original commit dates, messages, and authors
# ─────────────────────────────────────────────────────────

REPO_DIR="${1:-.}"
cd "$REPO_DIR"

echo "=== Backing up repo ==="
BACKUP_DIR="${REPO_DIR}.backup.$(date +%s)"
cp -r "$REPO_DIR" "$BACKUP_DIR" 2>/dev/null || true

echo "=== Removing __pycache__ and .egg-info from history ==="
# Clean these out first — they're generated artifacts
git filter-branch --force --tree-filter '
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
' --tag-name-filter cat -- --all

echo "=== Rewriting history: dockmanr → Dockmeister ==="
git filter-branch --force --tree-filter '
    # 1. Replace content in all text files (case variations)
    find . -type f \
        -not -path "./.git/*" \
        -not -name "*.pyc" \
        -not -name "*.db" \
        -not -name "*.sqlite" \
        -not -name "*.png" \
        -not -name "*.jpg" \
        -not -name "*.ico" | while read -r file; do
        if file "$file" | grep -q "text\|JSON\|XML\|empty"; then
            sed -i \
                -e "s/DockmanR/Dockmeister/g" \
                -e "s/dockmanr/dockmeister/g" \
                -e "s/DOCKMANR/DOCKMEISTER/g" \
                "$file" 2>/dev/null || true
        fi
    done

    # 2. Rename files containing dockmanr (deepest first to avoid path issues)
    find . -depth -not -path "./.git/*" -name "*dockmanr*" | while read -r path; do
        dir=$(dirname "$path")
        base=$(basename "$path")
        newbase=$(echo "$base" | sed -e "s/DockmanR/Dockmeister/g" -e "s/dockmanr/dockmeister/g")
        if [ "$base" != "$newbase" ]; then
            mv "$path" "$dir/$newbase"
        fi
    done

    # 3. Rename files containing DockmanR
    find . -depth -not -path "./.git/*" -name "*DockmanR*" | while read -r path; do
        dir=$(dirname "$path")
        base=$(basename "$path")
        newbase=$(echo "$base" | sed -e "s/DockmanR/Dockmeister/g" -e "s/dockmanr/dockmeister/g")
        if [ "$base" != "$newbase" ]; then
            mv "$path" "$dir/$newbase"
        fi
    done
' --tag-name-filter cat -- --all

echo "=== Cleaning up refs ==="
git for-each-ref --format='delete %(refname)' refs/original/ | git update-ref --stdin
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "=== Done ==="
echo "Verify with:"
echo "  git log --format='%ai %s'"
echo "  grep -ri dockmanr --include='*.py' ."
echo ""
echo "When satisfied, force push:"
echo "  git remote set-url origin git@github.com:Nihilentropy-117/Dockmeister.git"
echo "  git push --force origin main"
