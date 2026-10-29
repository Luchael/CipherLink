"""Keep README downloads tied to files that actually exist in a GitHub release.

Never publishes a release or changes repository visibility. GitHub errors are
captured because CLI errors may include authenticated download URLs.
"""
import argparse
import base64
import json
import re
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
START='<!-- cipherlink-downloads -->'
END='<!-- /cipherlink-downloads -->'
REPOSITORY='Luchael/CipherLink'


def run(args):
    result=subprocess.run(args,cwd=ROOT,capture_output=True,text=True)
    if result.returncode:raise RuntimeError('GitHub download-link update failed; raw response withheld')
    return result.stdout


def safe_url(url,repository,kind):
    parsed=urlsplit(str(url))
    if (parsed.scheme!='https' or parsed.netloc!='github.com' or parsed.query or parsed.fragment
            or not parsed.path.startswith('/'+repository+'/releases/'+kind+'/')):
        raise ValueError('Unexpected release URL')
    return url


def render_release(metadata,version,repository=REPOSITORY):
    if not re.fullmatch(r'\d+\.\d+\.\d+',version):raise ValueError('Invalid version')
    page=safe_url(metadata['url'],repository,'tag')
    assets={a['name']:a for a in metadata.get('assets',[]) if isinstance(a,dict) and a.get('size',0)>0}
    lines=[START,f'### 설치 파일 · {version}','']
    if metadata.get('isDraft'):
        lines+=['**GitHub 저장소 소유자 계정으로 로그인한 뒤 다운로드하세요.**','']
    choices=[('CipherLink-Windows-Setup.exe','**Windows 설치·업데이트 다운로드**'),
             ('CipherLink-Windows.exe','Windows 무설치 실행 파일'),
             ('CipherLink-Android.apk','Android APK 다운로드')]
    count=0
    for name,label in choices:
        if name in assets:
            url=safe_url(assets[name]['url'],repository,'download')
            lines.append(f'- [{label}]({url})');count+=1
    if not count:raise ValueError('No actual download files')
    if 'CipherLink-Android.apk' not in assets:lines+=['','Android APK는 아직 GitHub에 업로드되지 않았습니다.']
    lines+=['',f'[버전 상세 및 파일 목록]({page})','',END]
    return '\n'.join(lines)


def update_readme(readme,block,version):
    if readme.count(START)!=1 or readme.count(END)!=1:raise ValueError('README download markers missing or ambiguous')
    a=readme.index(START);b=readme.index(END)+len(END)
    old=re.search(r'### 설치 파일 · (\d+)\.(\d+)\.(\d+)',readme[a:b])
    if old and tuple(map(int,old.groups()))>tuple(map(int,version.split('.'))):return readme
    return readme[:a]+block+readme[b:]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('version');parser.add_argument('--github',action='store_true')
    args=parser.parse_args()
    if not re.fullmatch(r'\d+\.\d+\.\d+',args.version):parser.error('Invalid version')
    metadata=json.loads(run(['gh','release','view','v'+args.version,'--repo',REPOSITORY,'--json','url,isDraft,assets']))
    block=render_release(metadata,args.version)
    if not args.github:
        path=ROOT/'README.md';path.write_text(update_readme(path.read_text(encoding='utf-8'),block,args.version),encoding='utf-8')
        print('README actual release links updated');return
    # Modify only the current README, using its SHA to avoid overwriting another commit.
    path=f'repos/{REPOSITORY}/contents/README.md'
    current=json.loads(run(['gh','api',path+'?ref=main']))
    old=base64.b64decode(current['content']).decode('utf-8')
    new=update_readme(old,block,args.version)
    if old==new:print('README links already current');return
    payload={'message':f'Update actual download links for {args.version}','branch':'main','sha':current['sha'],
             'content':base64.b64encode(new.encode('utf-8')).decode('ascii')}
    with tempfile.TemporaryDirectory() as directory:
        file=Path(directory)/'readme-update.json';file.write_text(json.dumps(payload),encoding='utf-8')
        run(['gh','api','--method','PUT',path,'--input',str(file)])
    print('GitHub README download links updated')

if __name__=='__main__':main()
