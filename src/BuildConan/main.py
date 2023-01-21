import argparse
import sys
import subprocess

from .conan import build_all, upload_all

def parse():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', '-v', action='count', default=0)
    subparsers = parser.add_subparsers(dest='cmd', help='command help')
    for cmd in ('build', 'create', 'upload'):
        p= subparsers.add_parser(cmd, help=cmd + ' help')
        if cmd not in ('upload',):
            p.add_argument('--build', '-b', default='outdated', help='build missing')
            p.add_argument('--profile', '-pr', action='append', help='profile')
            p.add_argument('--profile:build', '-pr:b', dest='profile_build', default='', help='profile build')
        p.add_argument('--channel', '-c', help='conan channel')
        p.add_argument('--repo', '-r', help='artifactory repository')
        p.add_argument('paths', metavar='paths', nargs='+', help='build directories')
    args = parser.parse_args()
    kwargs = vars(args)
    cmd = kwargs.pop('cmd')
    paths = kwargs.pop('paths')
    args = []
    profiles = kwargs.pop('profile', None)
    if profiles:
        for profile in profiles:
            args += ['-pr', profile]
    profile_build = kwargs.pop('profile_build', None)
    if profile_build:
        args += ['-pr:b', profile_build]
    kwargs['args'] = args
    return cmd, paths, kwargs

def run():
    try:
        cmd, paths, kwargs = parse()
        if cmd == 'upload':
            upload_all(*paths, **kwargs)
        else:
            build_all(*paths, cmd=cmd, **kwargs)
    except subprocess.CalledProcessError as err:
        sys.exit(err.returncode)
