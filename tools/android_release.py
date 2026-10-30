"""Sign or verify a release APK without printing or publishing private key material."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile

from check_apk_update import inspect
from release_metadata import ROOT, project_version


def command(args):
    result = subprocess.run(args, cwd=ROOT, capture_output=True)
    if result.returncode:
        raise RuntimeError('Android release operation failed; private output withheld')
    return result.stdout


def verify(apk, build_tools, version_code, config):
    identity = inspect(apk, build_tools)
    if (identity.package != config['android_package'] or identity.version != version_code
            or identity.signers != frozenset([config['android_signer_sha256']])):
        raise ValueError('APK package, version code or signing certificate mismatch')
    with zipfile.ZipFile(apk) as archive:
        if archive.testzip() is not None:
            raise ValueError('APK archive integrity failure')


def prepare(output, unsigned=None):
    version, code = project_version()
    config = json.loads((ROOT / 'release-config.json').read_text(encoding='utf-8'))
    sdk = Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT']) / 'build-tools/35.0.0'
    output.parent.mkdir(parents=True, exist_ok=True)
    # A temporary folder lives outside app assets and is always removed after signing.
    with tempfile.TemporaryDirectory(prefix='cipherlink-sign-', dir=os.environ.get('RUNNER_TEMP')) as temporary:
        folder = Path(temporary)
        key_value = os.environ.get('ANDROID_KEYSTORE_BASE64')
        local_key = os.environ.get('CIPHERLINK_KEYSTORE_FILE')
        if key_value or local_key:
            if unsigned is None or not unsigned.is_file():
                raise ValueError('Unsigned release APK is required')
            if key_value:
                key = folder / 'release.p12'
                key.write_bytes(base64.b64decode(''.join(key_value.split()), validate=True))
                key.chmod(0o600)
                if not os.environ.get('ANDROID_KEYSTORE_PASSWORD'):
                    raise ValueError('ANDROID_KEYSTORE_PASSWORD Secret is missing')
                password_file = folder / 'password.txt'
                password_file.write_text(os.environ['ANDROID_KEYSTORE_PASSWORD'].rstrip('\r\n') + '\n', encoding='utf-8')
                password_file.chmod(0o600)
                password = 'file:' + str(password_file)
            else:
                key = Path(local_key)
                password_file = Path(os.environ['CIPHERLINK_KEYSTORE_PASSWORD_FILE'])
                password = 'file:' + str(password_file)
            command([str(sdk / 'zipalign'), '-f', '4', str(unsigned), str(folder / 'aligned.apk')])
            command([str(sdk / 'apksigner'), 'sign', '--ks', str(key), '--ks-key-alias', config['android_key_alias'],
                     '--ks-pass', password, '--out', str(output), str(folder / 'aligned.apk')])
        else:
            raise ValueError('Configure ANDROID_KEYSTORE_BASE64 and ANDROID_KEYSTORE_PASSWORD Secrets')
        verify(output, sdk, code, config)
    print('Android package, version, certificate and archive verified')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--unsigned', type=Path)
    args = parser.parse_args()
    try:
        prepare(args.output.resolve(), args.unsigned.resolve() if args.unsigned else None)
    except Exception as exc:
        raise SystemExit('Android release stopped: ' + type(exc).__name__ + '; private output withheld')


if __name__ == '__main__':
    main()
