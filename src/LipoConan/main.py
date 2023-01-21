import sys
import subprocess

from .conan import conan_install

def run(args=None):
    try:
        if args is None:
            args = sys.argv[1:]
        if sys.platform == 'darwin':
            profiles = []
            install_args = []
            i = 0
            while i < len(args):
                if args[i] in ('-pr', '-pr:h'):
                    profiles.append(args[i + 1])
                    i += 1
                else:
                    install_args.append(args[i])
                i += 1
            if len(profiles) > 1:
                conan_install(install_args, profiles)
                return
        subprocess.run(['conan', 'install'] + args, check=True)
    except subprocess.CalledProcessError as err:
        sys.exit(err.returncode)
