"""Check public APK identity before calling a build an in-place update.

This verifies APK integrity and metadata, not device installation restrictions.
No keystore, passwords, account data or APK asset contents are accessed.
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import os
import re
import subprocess


@dataclass(frozen=True)
class Identity:
    package: str
    version: int
    signers: frozenset[str]


def inspect(apk: Path, build_tools: Path) -> Identity:
    verified = subprocess.run(
        [str(build_tools / 'apksigner'), 'verify', '--print-certs', str(apk)],
        capture_output=True, text=True, check=True)
    signers = frozenset(re.findall(r'certificate SHA-256 digest: ([a-fA-F0-9]{64})',
                                   verified.stdout))
    badging = subprocess.run([str(build_tools / 'aapt2'), 'dump', 'badging', str(apk)],
                             capture_output=True, text=True, check=True)
    match = re.search(r"^package: name='([^']+)' versionCode='(\d+)'", badging.stdout, re.M)
    if not match or not signers:
        raise ValueError('APK identity unavailable')
    return Identity(match[1], int(match[2]), signers)


def check_update(installed: Identity, candidate: Identity) -> str:
    if installed.package != candidate.package:
        return 'SEPARATE_APPLICATION'
    if installed.signers != candidate.signers:
        # Signing-key rotation needs a separately verified signing lineage.
        return 'SIGNATURE_MISMATCH'
    if candidate.version <= installed.version:
        return 'VERSION_NOT_HIGHER'
    return 'UPDATE_METADATA_COMPATIBLE'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installed_apk', type=Path)
    parser.add_argument('candidate_apk', type=Path)
    parser.add_argument('--build-tools', type=Path, default=Path(
        os.environ.get('ANDROID_HOME', '/workspace/.tools/android-sdk')) / 'build-tools/35.0.0')
    args = parser.parse_args()
    try:
        before = inspect(args.installed_apk, args.build_tools)
        after = inspect(args.candidate_apk, args.build_tools)
    except (OSError, ValueError, subprocess.CalledProcessError):
        print('APK_VERIFICATION_FAILED')
        return 3
    result = check_update(before, after)
    print(result)
    print(f'Package: {before.package} -> {after.package}; version: {before.version} -> {after.version}')
    return 0 if result == 'UPDATE_METADATA_COMPATIBLE' else 2 if result == 'SEPARATE_APPLICATION' else 1


if __name__ == '__main__':
    raise SystemExit(main())
