"""Publish a signed APK draft, then let Windows CI build and finish the release.

Signing stays on this machine: never uploads a keystore or requests user secrets.
Requires the existing Android SDK/keystore, Gradle, JDK17 and authenticated gh CLI.
"""
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from check_apk_update import inspect
from release_metadata import ROOT, project_version


def command(args, phase):
    result = subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    if result.returncode:
        # CLI failures may contain signed URLs. Keep them out of console output.
        raise SystemExit(f'{phase} failed (exit {result.returncode}); no credentials or raw URLs shown')
    print(phase+' OK',flush=True)
    return result.stdout.strip()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version')
    parser.add_argument('--output',type=Path)
    parser.add_argument('--resume',action='store_true',help='Resume an existing draft after resolving upload access')
    parser.add_argument('--finalize',action='store_true',help='Publish a completed draft only when repository is private')
    args=parser.parse_args()
    version,code=project_version()
    if args.version != version: parser.error('Requested version must match PC and Android')
    config=json.loads((ROOT/'release-config.json').read_text(encoding='utf-8'))
    repo=config['repository'];tag=f'v{version}'
    if args.finalize:
        private=command(['gh','api',f'repos/{repo}','--jq','.private'],'Repository privacy check')
        if private != 'true': raise SystemExit('Repository is still public; the release remains a draft')
        metadata=json.loads(command(['gh','release','view',tag,'--repo',repo,'--json','isDraft,assets'],'Release asset check'))
        names={asset['name'] for asset in metadata['assets']}
        if not {'CipherLink-Windows.exe','CipherLink-Android.apk','SHA256SUMS.txt','update.json'}.issubset(names):
            raise SystemExit('Both binaries, checksums and metadata are required')
        if not metadata['isDraft']: raise SystemExit('Release is already published; no changes made')
        command(['gh','release','edit',tag,'--repo',repo,'--draft=false','--latest'],'Private release publication')
        return
    if command(['git','status','--porcelain'],'Worktree check'): parser.error('Commit changes before publishing')
    notes=ROOT/'docs/releases'/f'v{version}.md'
    if not notes.is_file(): parser.error('Release notes are missing')
    head=command(['git','rev-parse','HEAD'],'Source revision')
    command(['gradle','--no-daemon','--max-workers=3','--console=plain','-p','android',
             '-PcipherlinkPreview=true',':app:assembleDebug'],'Android build')
    sdk=Path(os.environ.get('ANDROID_HOME',os.environ.get('ANDROID_SDK_ROOT','')))
    apk=ROOT/'android/app/build/outputs/apk/debug/app-debug.apk'
    identity=inspect(apk,sdk/'build-tools/35.0.0')
    if (identity.package != config['android_package'] or identity.version != code or
            identity.signers != frozenset([config['android_signer_sha256']])):
        raise SystemExit('APK package/version/signature mismatch; release stopped')
    with zipfile.ZipFile(apk) as archive:
        if archive.testzip() is not None: raise SystemExit('APK integrity check failed')
    print('APK identity and integrity OK',flush=True)
    with tempfile.TemporaryDirectory(prefix='cipherlink-release-') as temporary:
        folder=Path(temporary);asset=folder/config['android_asset'];shutil.copyfile(apk,asset)
        if args.output:
            args.output.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(apk,args.output/f'CipherLink-{version}.apk')
        if args.resume:
            metadata=json.loads(command(['gh','release','view',tag,'--repo',repo,'--json','isDraft,assets'],'Existing draft check'))
            if not metadata['isDraft']: raise SystemExit('Cannot overwrite a published release')
            if config['android_asset'] in {entry['name'] for entry in metadata['assets']}:
                raise SystemExit('APK is already attached; run the release workflow to finish')
            target=command(['gh','api',f'repos/{repo}/git/ref/tags/{tag}','--jq','.object.sha'],'Tag revision')
            if command(['git','diff',target,'HEAD','--','android','pc'],'Tagged application source check'):
                raise SystemExit('Application source changed since the tag; create a new version')
        else:
            command(['git','tag',tag,head],'Version tag creation')
            command(['git','push','origin',f'refs/tags/{tag}'],'Version tag push')
            command(['gh','release','create',tag,'--repo',repo,'--target',head,'--draft',
                     '--title',f'사이퍼링크 {version}','--notes-file',str(notes)],'Draft release creation')
        command(['gh','release','upload',tag,str(asset),'--repo',repo],'APK upload')
    command(['gh','workflow','run','release.yml','--repo',repo,'--ref','main',
             '-f',f'version={version}'],'Windows build and release dispatch')
    print(f'https://github.com/{repo}/releases/tag/{tag}')
    print('Release remains a draft until the Windows build and both-file checks pass.')


if __name__ == '__main__':
    main()
