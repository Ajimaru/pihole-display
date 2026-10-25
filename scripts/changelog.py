#!/usr/bin/env python3
"""Turn a list of commits into release notes.

Reads TAB-separated "subject<TAB>hash" lines (what
``git log --pretty=$'%s\\t%h'`` produces) and groups them by their
conventional-commit prefix. Anything without a recognised prefix is listed
under "Other" rather than dropped, so a release note never silently loses a
change.

Used by .github/workflows/release.yml; runs standalone for a preview:

    git log --no-merges --pretty=$'%s\\t%h' v0.1.0..HEAD > commits.tsv
    VERSION=0.2.0 python3 scripts/changelog.py commits.tsv
"""

import os
import re
import sys

# Prefix -> heading, in the order the sections should appear.
SECTIONS = [
    ('feat', 'Features'),
    ('fix', 'Fixes'),
    ('perf', 'Performance'),
    ('docs', 'Documentation'),
    ('refactor', 'Refactoring'),
    ('test', 'Tests'),
    ('build', 'Build and CI'),
    ('ci', 'Build and CI'),
    ('chore', 'Build and CI'),
    ('style', 'Build and CI'),
]

# feat: ... / fix(web): ... / feat!: ... / refactor(ui)!: ...
PREFIX = re.compile(r'^(?P<type>[a-z]+)(?:\([^)]*\))?(?P<breaking>!)?: *(?P<rest>.*)$')


def parse(lines):
    """Group commits by section, keeping breaking changes separate."""
    headings = dict(SECTIONS)
    order = []
    for _, heading in SECTIONS:
        if heading not in order:
            order.append(heading)

    grouped = {heading: [] for heading in order}
    grouped['Other'] = []
    breaking = []

    for line in lines:
        subject, _, commit_hash = line.rstrip('\n').partition('\t')
        if not subject:
            continue
        entry_hash = f' ({commit_hash})' if commit_hash else ''
        match = PREFIX.match(subject)
        if match and match.group('type') in headings:
            text = match.group('rest').strip() or subject
            entry = f'- {text}{entry_hash}'
            if match.group('breaking'):
                breaking.append(entry)
            else:
                grouped[headings[match.group('type')]].append(entry)
        else:
            grouped['Other'].append(f'- {subject}{entry_hash}')

    return order, grouped, breaking


def render(order, grouped, breaking, version, previous, repository):
    """Build the release body."""
    out = ["## What's changed", '']

    if breaking:
        out += ['### Breaking changes', ''] + breaking + ['']

    for heading in order + ['Other']:
        entries = grouped.get(heading)
        if entries:
            out += [f'### {heading}', ''] + entries + ['']

    if not breaking and not any(grouped.values()):
        out += ['No changes recorded.', '']

    if version:
        out += [
            '## Install', '',
            '```bash',
            f'tar -xzf pihole-display-{version}.tar.gz',
            f'cd pihole-display-{version}',
            'sudo ./install.sh',
            '```',
            '',
        ]

    if previous and repository:
        tag = f'v{version}' if version else 'HEAD'
        out += [
            f'**Full changelog**: https://github.com/{repository}'
            f'/compare/{previous}...{tag}',
        ]

    return '\n'.join(out).rstrip() + '\n'


def main():
    """Read commits from a file or stdin and print the release notes."""
    if len(sys.argv) > 1:
        with open(sys.argv[1], encoding='utf-8') as handle:
            lines = handle.readlines()
    else:
        lines = sys.stdin.readlines()

    order, grouped, breaking = parse(lines)
    sys.stdout.write(render(
        order, grouped, breaking,
        version=os.environ.get('VERSION', ''),
        previous=os.environ.get('PREVIOUS', ''),
        repository=os.environ.get('GITHUB_REPOSITORY', ''),
    ))


if __name__ == '__main__':
    main()
