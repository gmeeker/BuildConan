import json
import os
import sys
import tempfile
from subprocess import run, DEVNULL, CalledProcessError

__all__ = ['read_recipe', 'upload_one', 'upload_all', 'build_one', 'build_all']

_mac_default_profile = ['-pr', 'x86_64', '-pr', 'armv8', '-pr:b', 'default']

def go(args, verbose=False, **kw):
    if verbose:
        print(' '.join(args))
    try:
        run(args, **kw, check=True)
    except CalledProcessError as err:
        sys.exit(err.returncode)

def read_recipe(build_dir, channel='', verbose=False):
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.close()
        go(['conan', 'inspect', '.', '--json', tmp.name], stdout=DEVNULL, cwd=build_dir, verbose=verbose)
        with open(tmp.name, encoding='utf-8') as f:
            package = json.loads(f.read())
    full_name = None
    if package['name'] and package['version']:
        full_name = f"{package['name']}/{package['version']}@{channel}"
    return full_name, package

def upload_one(build_dir, repo=None, channel='', args=(), verbose=False):
    if repo:
        full_name, _ = read_recipe(build_dir, channel, verbose=verbose)
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.close()
            go(['conan', 'info', full_name or '.', '-b', '--json', tmp.name],
               stdout=DEVNULL, cwd=build_dir, verbose=verbose)
            with open(tmp.name, encoding='utf-8') as f:
                refs = json.loads(f.read())
        if full_name:
            refs.append(full_name)
        for ref in refs:
            go(['conan', 'upload', ref, '--all', '-c', '-r', repo] + list(args), cwd=build_dir, verbose=verbose)

def upload_all(*paths, **kw):
    for i in paths:
        upload_one(i, **kw)

def build_one(build_dir, repo=None, cmd='create', build='outdated', channel='', args=(), verbose=False):
    if build:
        b = ['--build=' + build]
    else:
        b = []
    if cmd == 'build':
        install = ['conan', 'install']
        profiles = []
        if sys.platform == 'darwin':
            install = ['conan-lipo']
            if '-pr' not in args:
                profiles = list(_mac_default_profile)
        go(install + ['.', channel, '-u'] + b + list(args) + profiles, cwd=build_dir, verbose=verbose)
        go(['conan', 'build', '.'], cwd=build_dir, verbose=verbose)
    else:
        go(['conan', cmd, '.', channel, '-u'] + b + list(args), cwd=build_dir, verbose=verbose)

def build_all(*paths, **kw):
    for i in paths:
        build_one(i, **kw)
