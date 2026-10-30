"""Create an immutable version tag and skip already-complete releases."""
import json
import os
import re
import subprocess
from release_metadata import project_version


def run(args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError('Release planning failed; raw output withheld')
    return result.stdout.strip()


def main():
    version, _ = project_version()
    requested = os.environ.get('REQUESTED_VERSION', '').removeprefix('v')
    if requested and requested != version:
        raise ValueError('Requested version does not match checked-out source')
    tag = 'v' + version
    head = run(['git', 'rev-parse', 'HEAD'])
    if not re.fullmatch(r'[a-f0-9]{40}', head):
        raise ValueError('Invalid source commit')
    existing = subprocess.run(['git', 'rev-parse', '--verify', 'refs/tags/' + tag], capture_output=True, text=True)
    if existing.returncode == 0:
        run(['git', 'diff', '--exit-code', tag, head, '--', 'android', 'pc'])
        head = run(['git', 'rev-list', '-n', '1', tag])
    else:
        run(['git', 'tag', tag, head])
        run(['git', 'push', 'origin', 'refs/tags/' + tag])
    release = subprocess.run(['gh', 'release', 'view', tag, '--json', 'isDraft,assets'], capture_output=True, text=True)
    complete = False
    if release.returncode == 0:
        data = json.loads(release.stdout)
        names = {row['name'] for row in data.get('assets', []) if row.get('size', 0) > 0}
        complete = not data['isDraft'] and {'CipherLink-Windows-Setup.exe', 'CipherLink-Windows.exe', 'CipherLink-Android.apk', 'SHA256SUMS.txt', 'update.json'} <= names
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as out:
        out.write(f'version={version}\nsource={head}\npublish={str(not complete).lower()}\n')
    print('Release already complete' if complete else 'Release source pinned to ' + tag)


if __name__ == '__main__':
    main()
