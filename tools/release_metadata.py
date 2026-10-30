"""Version and file-integrity checks shared by local publishing and GitHub CI."""
import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def project_version(root=ROOT):
    pc = re.search(r'__version__ = "([^"]+)"', (root/'pc/gametodo/__init__.py').read_text(encoding='utf-8')).group(1)
    android = (root/'android/app/build.gradle.kts').read_text(encoding='utf-8')
    mobile = re.search(r'versionName = "([^"]+)"', android).group(1)
    code = int(re.search(r'versionCode = (\d+)', android).group(1))
    if pc != mobile or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', pc):
        raise ValueError('PC/Android semantic versions must match')
    resource=root/'pc/assets/version_info.txt'
    if resource.is_file():
        text=resource.read_text(encoding='utf-8')
        expected=tuple(map(int,pc.split('.')))+(0,)
        for value in re.findall(r'(?:filevers|prodvers)=\(([^)]+)\)',text):
            if tuple(map(int,value.split(',')))!=expected:raise ValueError('Windows file version does not match source')
        for value in re.findall(r"StringStruct\('(?:FileVersion|ProductVersion)', '([^']+)'\)",text):
            if value!=pc+'.0':raise ValueError('Windows display version does not match source')
    return pc, code


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def manifest(directory, version, code, windows_only=False):
    assets = {'windows': 'CipherLink-Windows.exe'}
    if not windows_only: assets['android'] = 'CipherLink-Android.apk'
    else: assets['windows_installer'] = 'CipherLink-Windows-Setup.exe'
    if not all((directory/name).is_file() and (directory/name).stat().st_size > 0 for name in assets.values()):
        raise ValueError('Required release assets must be present and non-empty')
    installer='CipherLink-Windows-Setup.exe'
    if (directory/installer).is_file():assets['windows_installer']=installer
    return {'version': version, 'android_version_code': None if windows_only else code,
            **{platform: {'name': name, 'sha256': digest(directory/name)} for platform, name in assets.items()}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('version')
    parser.add_argument('--directory', type=Path)
    parser.add_argument('--windows-only', action='store_true', help='Publish verified Windows assets without claiming an Android update')
    args = parser.parse_args()
    version, code = project_version()
    if args.version != version:
        parser.error('Tag version does not match source versions')
    if args.directory:
        result = manifest(args.directory,version,code,windows_only=args.windows_only)
        (args.directory/'update.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (args.directory/'SHA256SUMS.txt').write_text(''.join(
            f"{result[p]['sha256']}  {result[p]['name']}\n" for p in ('windows_installer','windows','android') if p in result),encoding='utf-8')
    print(f'RELEASE_VERSION_OK {version}; Android code {code}')


if __name__ == '__main__':
    main()
