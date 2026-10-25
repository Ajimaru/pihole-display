#!/bin/bash
# ============================================================
# release.sh — cut a release: set version.py, commit, tag, push
#
#   ./scripts/release.sh 0.1.0
#   ./scripts/release.sh 0.1.0 --dry-run
#
# Pushing the tag triggers .github/workflows/release.yml, which builds the
# archive and publishes the GitHub release.
# ============================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VERSION_FILE="$REPO_ROOT/pihole-display/version.py"

die() { echo "error: $*" >&2; exit 1; }

# ── Arguments ────────────────────────────────────────────────

VERSION=""
DRY_RUN=0
for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        -h|--help)
            cat <<'USAGE'
release.sh - cut a release: set version.py, commit, tag

  ./scripts/release.sh 0.1.0
  ./scripts/release.sh 0.1.0 --dry-run

Pushing the tag afterwards triggers .github/workflows/release.yml, which
builds the archive and publishes the GitHub release.
USAGE
            exit 0
            ;;
        -*) die "unknown option: $arg" ;;
        *)  [ -n "$VERSION" ] && die "version given twice"
            VERSION="$arg" ;;
    esac
done

[ -n "$VERSION" ] || die "usage: $0 <version> [--dry-run]"
# Plain MAJOR.MINOR.PATCH, optionally a prerelease like 1.2.0-rc1
[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[0-9A-Za-z.]+)?$ ]] \
    || die "version must look like 1.2.3 or 1.2.3-rc1, got '$VERSION'"

TAG="v$VERSION"

# ── Checks ───────────────────────────────────────────────────

cd "$REPO_ROOT"

git rev-parse --git-dir >/dev/null 2>&1 || die "not a git repository"

CURRENT=$(sed -n "s/^__version__ = '\(.*\)'$/\1/p" "$VERSION_FILE")
[ -n "$CURRENT" ] || die "cannot read __version__ from $VERSION_FILE"

echo "Current: $CURRENT"
echo "New:     $VERSION"
echo

# A dirty tree would put unrelated changes into the release commit.
if [ -n "$(git status --porcelain)" ]; then
    echo "Uncommitted changes:"
    git status --short | sed 's/^/  /'
    die "commit or stash them first"
fi

git rev-parse "$TAG" >/dev/null 2>&1 && die "tag $TAG already exists"

BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "Branch:  $BRANCH"

# Syntax check: a release that cannot even be parsed is worthless.
python3 -m compileall -q pihole-display/*.py \
    || die "pihole-display/*.py does not compile"

# ── Apply ────────────────────────────────────────────────────

if [ "$DRY_RUN" -eq 1 ]; then
    echo
    echo "Dry run — would do:"
    echo "  set $VERSION_FILE to $VERSION"
    echo "  git commit -m 'release: $TAG'"
    echo "  git tag -a $TAG"
    echo "  git push origin $BRANCH $TAG"
    exit 0
fi

# Same substitution the workflow reads back, so the two cannot disagree.
python3 - "$VERSION_FILE" "$VERSION" <<'PY'
import re
import sys

path, version = sys.argv[1], sys.argv[2]
with open(path, encoding='utf-8') as f:
    text = f.read()
new, count = re.subn(
    r"^__version__ = '.*'$",
    f"__version__ = '{version}'",
    text,
    count=1,
    flags=re.MULTILINE,
)
if count != 1:
    sys.exit(f'could not rewrite __version__ in {path}')
with open(path, 'w', encoding='utf-8') as f:
    f.write(new)
PY

WRITTEN=$(sed -n "s/^__version__ = '\(.*\)'$/\1/p" "$VERSION_FILE")
[ "$WRITTEN" = "$VERSION" ] || die "version.py now says '$WRITTEN'"

git add "$VERSION_FILE"
git commit -q -m "release: $TAG"
git tag -a "$TAG" -m "$TAG"

echo
echo "Committed and tagged $TAG."
echo "Push to publish the release:"
echo "  git push origin $BRANCH $TAG"
