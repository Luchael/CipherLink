"""Transfer an APK to a draft using encrypted temporary Git objects.

The receiver's temporary RSA private key never leaves its Actions runner.
Only a public key and encrypted APK enter Git; signing keys are never transferred.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

ROOT=Path(__file__).resolve().parents[1]
REQUEST=ROOT/'.github/apk-transfer-request.json'


def run(args,data=None):
    result=subprocess.run(args,input=data,cwd=ROOT,capture_output=True)
    if result.returncode:raise RuntimeError('Transfer operation failed; raw output withheld')
    return result.stdout


def publish(file,ref):
    blob=run(['git','hash-object','-w','--stdin'],file.read_bytes()).decode().strip()
    tree=run(['git','mktree'],f'100644 blob {blob}\tartifact\n'.encode()).decode().strip()
    commit=run(['git','-c','user.name=CipherLink transfer','-c','user.email=transfer@users.noreply.github.com',
                'commit-tree',tree,'-m','Temporary encrypted APK transport']).decode().strip()
    run(['git','push','origin',f'{commit}:refs/heads/{ref}'])


def fetch(ref):
    result=subprocess.run(['git','ls-remote','origin','refs/heads/'+ref],cwd=ROOT,capture_output=True)
    if result.returncode:raise RuntimeError('Git connection unavailable')
    if not result.stdout.strip():return None
    run(['git','fetch','--no-tags','origin','refs/heads/'+ref])
    return run(['git','show','FETCH_HEAD:artifact'])


def wait(ref):
    for _ in range(100):
        data=fetch(ref)
        if data is not None:return data
        time.sleep(5)
    raise RuntimeError('Transfer timed out')


def main():
    request=json.loads(REQUEST.read_text())
    identity=request['transfer_id'];version=request['version'];digest=request['sha256']
    if not re.fullmatch(r'[a-f0-9]{32}',identity) or not re.fullmatch(r'\d+\.\d+\.\d+',version) or not re.fullmatch(r'[a-f0-9]{64}',digest):
        raise ValueError('Invalid transfer request')
    key_ref='apk-public-key-'+identity;data_ref='apk-encrypted-'+identity
    aad=(identity+':'+digest).encode()
    if sys.argv[1]=='send':
        apk=Path(sys.argv[2]);plain=apk.read_bytes()
        if hashlib.sha256(plain).hexdigest()!=digest:raise ValueError('APK hash mismatch')
        public=serialization.load_pem_public_key(wait(key_ref))
        if not isinstance(public,rsa.RSAPublicKey) or public.key_size!=3072:raise ValueError('Unexpected receiver key')
        key=os.urandom(32);nonce=os.urandom(12)
        encrypted_key=public.encrypt(key,padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
        encrypted=b'CLAPK01'+encrypted_key+nonce+AESGCM(key).encrypt(nonce,plain,aad)
        with tempfile.TemporaryDirectory() as directory:
            file=Path(directory)/'encrypted.bin';file.write_bytes(encrypted);publish(file,data_ref)
        print('Encrypted APK transferred; awaiting receiver validation',flush=True)
        return
    if sys.argv[1]!='receive':raise ValueError('Unknown transfer mode')
    metadata=json.loads(run(['gh','release','view','v'+version,'--json','isDraft,assets']))
    if not metadata['isDraft']:raise ValueError('A private draft is required')
    if any(a['name']=='CipherLink-Android.apk' for a in metadata['assets']):raise ValueError('APK already attached')
    private=rsa.generate_private_key(public_exponent=65537,key_size=3072)
    try:
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory);public=folder/'public.pem'
            public.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM,serialization.PublicFormat.SubjectPublicKeyInfo))
            publish(public,key_ref)
            print('Receiver ready; public key available',flush=True)
            data=wait(data_ref)
            if data[:7]!=b'CLAPK01' or len(data)<419:raise ValueError('Invalid encrypted payload')
            key=private.decrypt(data[7:391],padding.OAEP(mgf=padding.MGF1(hashes.SHA256()),algorithm=hashes.SHA256(),label=None))
            plain=AESGCM(key).decrypt(data[391:403],data[403:],aad)
            if hashlib.sha256(plain).hexdigest()!=digest:raise ValueError('APK hash mismatch')
            apk=folder/'CipherLink-Android.apk';apk.write_bytes(plain)
            from check_apk_update import inspect
            from release_metadata import project_version
            config=json.loads((ROOT/'release-config.json').read_text())
            actual_version,code=project_version()
            if actual_version!=version:raise ValueError('Source version mismatch')
            sdk=Path(os.environ.get('ANDROID_HOME') or os.environ['ANDROID_SDK_ROOT'])/'build-tools'
            tools=sorted((p for p in sdk.iterdir() if (p/'apksigner').is_file()),reverse=True)[0]
            actual=inspect(apk,tools)
            if actual.package!=config['android_package'] or actual.version!=code or actual.signers!=frozenset([config['android_signer_sha256']]):
                raise ValueError('APK package, version or signer mismatch')
            run(['gh','release','upload','v'+version,str(apk)])
            run([sys.executable,'tools/update_download_links.py',version,'--github'])
            print('APK verified and attached to draft; README updated',flush=True)
    finally:
        for ref in (key_ref,data_ref):
            subprocess.run(['git','push','origin','--delete',ref],cwd=ROOT,capture_output=True)

if __name__=='__main__':
    try:main()
    except Exception as exc:raise SystemExit('APK transfer failed: '+type(exc).__name__+'; private data withheld')
