#!/usr/bin/env python3
"""Create a genuine GitHub fork, overlay this adaptation, validate and publish.

Run on an authenticated workstation with gh, git, node and Python >=3.11.
No remote action was performed when this release package was created.
Existing destination repositories are refused by default; no force pushes.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

UPSTREAM='basvandervelden/ai_food_safety_review'
ROOT=Path(__file__).resolve().parents[1]
COPY_DIRS=('agent','assets','config','data','docs','scripts','tests','.github')
COPY_FILES=('README.md','START_HERE.md','NOTICE.md','LICENSE','CITATION.cff','.gitignore','requirements-dev.txt','pyproject.toml','index.html','Enzyme_Evidence_Atlas.html')

class PublishError(RuntimeError): pass

def run(args,cwd=None,capture=False):
    print('+ '+' '.join(str(a) for a in args),flush=True)
    p=subprocess.run([str(a) for a in args],cwd=cwd,text=True,stdout=subprocess.PIPE if capture else None,stderr=subprocess.PIPE if capture else None)
    if p.returncode:
        raise PublishError((p.stderr.strip() if capture else '') or f'Command failed with status {p.returncode}')
    return p.stdout.strip() if capture else ''

def repo_metadata(repo):
    p=subprocess.run(['gh','api',f'repos/{repo}'],text=True,capture_output=True)
    if p.returncode:
        if '(HTTP 404)' in p.stderr: return None
        raise PublishError(p.stderr.strip() or 'Could not inspect destination repository')
    return json.loads(p.stdout)

def copy_release(destination):
    """Replace upstream code/data, retaining .git and its complete ancestry."""
    for name in COPY_DIRS:
        target=destination/name
        if target.exists():shutil.rmtree(target)
        shutil.copytree(ROOT/name,target,ignore=shutil.ignore_patterns('__pycache__','*.pyc','.pytest_cache'))
    for name in COPY_FILES:
        if (ROOT/name).exists():shutil.copy2(ROOT/name,destination/name)
    # Remove the source project's launch text rather than leave food-safety instructions.
    legacy=destination/'START_HERE_NL.txt'
    if legacy.exists():legacy.unlink()

def main(argv=None):
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--name',default='enzyme-evidence-atlas',help='New repository name under the authenticated GitHub user')
    ap.add_argument('--update-existing',action='store_true',help='Explicitly replace code/data in an existing fork of the exact upstream; review your remote backup first')
    ap.add_argument('--no-publish',action='store_true',help='Create fork and push adaptation, but leave Pages and refresh disabled')
    args=ap.parse_args(argv)
    import re
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,99}',args.name):ap.error('Invalid repository name')
    for command in ('gh','git','node'):
        if not shutil.which(command):ap.error(f'Missing {command}. Install prerequisites listed in START_HERE.md.')
    if sys.version_info<(3,11):ap.error('Python 3.11 or newer is required')
    try:
        # All deterministic checks happen before the first remote write.
        run([sys.executable,'-m','unittest','discover','-s','tests','-t','.','-v'],ROOT)
        run(['node','--check','assets/app.js'],ROOT)
        run([sys.executable,'-m','agent.render_static'],ROOT)
        run(['gh','auth','status'])
        user=run(['gh','api','user','--jq','.login'],capture=True)
        repo=user+'/'+args.name
        metadata=repo_metadata(repo)
        if metadata is not None:
            if not args.update_existing:raise PublishError(f'{repo} already exists. Nothing changed. Use a fresh --name, or explicitly --update-existing only after reviewing the existing fork.')
            if not metadata.get('fork') or metadata.get('parent',{}).get('full_name')!=UPSTREAM:raise PublishError('Existing repository is not a fork of the exact upstream; refusing to overwrite')
        else:
            run(['gh','repo','fork',UPSTREAM,'--fork-name',args.name,'--clone=false','--remote=false'])
            for _ in range(12):
                metadata=repo_metadata(repo)
                if metadata is not None:break
                time.sleep(2)
            if metadata is None:raise PublishError('Fork request submitted, but the fork was not yet available. No code pushed.')
        run(['gh','auth','setup-git'])
        with tempfile.TemporaryDirectory(prefix='enzyme-evidence-publish-') as temp:
            dest=Path(temp)/'repo'
            run(['git','clone',f'https://github.com/{repo}.git',dest])
            branch=metadata.get('default_branch','main')
            if branch!='main':raise PublishError('Expected default branch main; configure workflows for the fork branch before publishing')
            copy_release(dest)
            run([sys.executable,'-m','unittest','discover','-s','tests','-t','.','-v'],dest)
            run([sys.executable,'-m','agent.render_static'],dest)
            run(['git','config','user.name',user],dest)
            run(['git','config','user.email',user+'@users.noreply.github.com'],dest)
            run(['git','add','--all'],dest)
            changed=subprocess.run(['git','diff','--cached','--quiet'],cwd=dest).returncode
            if changed:
                run(['git','commit','-m','feat: adapt living review to enzyme evidence; credit Bas van der Velden'],dest)
                run(['git','push','origin','HEAD:main'],dest)  # Deliberately never force.
            head=run(['git','rev-parse','HEAD'],dest,capture=True)
        print(f'Fork with adapted code: https://github.com/{repo}')
        if args.no_publish:
            print('Pages and automated retrieval were intentionally not activated.');return 0
        pages=subprocess.run(['gh','api',f'repos/{repo}/pages'],capture_output=True,text=True)
        if pages.returncode and '(HTTP 404)' not in pages.stderr:raise PublishError(pages.stderr.strip()+'\nCode was pushed, but Pages configuration failed.')
        run(['gh','api','--method','PUT' if pages.returncode==0 else 'POST',f'repos/{repo}/pages','-f','build_type=workflow'])
        run(['gh','variable','set','PUBLISH_PAGES','--repo',repo,'--body','true'])
        run(['gh','variable','set','ENABLE_REFRESH','--repo',repo,'--body','true'])
        run(['gh','workflow','enable','refresh.yml','--repo',repo])
        run(['gh','workflow','enable','publish.yml','--repo',repo])
        run(['gh','workflow','run','publish.yml','--repo',repo,'--ref','main'])
        run_id=None
        for _ in range(15):
            runs=json.loads(run(['gh','run','list','--repo',repo,'--workflow','publish.yml','--event','workflow_dispatch','--limit','5','--json','databaseId,headSha'],capture=True))
            found=next((r for r in runs if r['headSha']==head),None)
            if found:run_id=str(found['databaseId']);break
            time.sleep(2)
        if not run_id:raise PublishError('Publishing was requested but a matching run was not found. Inspect the Actions tab; no successful deployment is being claimed.')
        run(['gh','run','watch',run_id,'--repo',repo,'--exit-status'])
        url=run(['gh','api',f'repos/{repo}/pages','--jq','.html_url'],capture=True)
        print('Successful Pages workflow: '+url)
        print('Weekly refresh enabled. Its first external search still needs to complete successfully; run the Refresh enzyme literature workflow to verify it now.')
        return 0
    except (PublishError,OSError,ValueError) as exc:
        print('STOPPED: '+str(exc),file=sys.stderr)
        print('Earlier successful operations are not automatically undone. See START_HERE.md for recovery.',file=sys.stderr)
        return 1

if __name__=='__main__':raise SystemExit(main())
