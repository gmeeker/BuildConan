import json
import os
import shutil
import tempfile
from subprocess import run

from .lipo import lipo


__all__ = ['replace_file', 'conan_install']

_filenames = ('conanbuildinfo.cmake', 'conanbuildinfo.txt', 'SConscript_conan')


def replace_file(filename, find_replace_pairs, custom_replace=None):
    with open(filename, 'r+', encoding='utf-8') as f:
        data = f.read()
        for find, replace in find_replace_pairs:
            data = data.replace(find, replace)
        if custom_replace:
            data = custom_replace(data)
        f.seek(0)
        f.write(data)


def replace_libs_line(line, lib_map):
    if 'LIBS' in line:
        for lib, new_libs in lib_map:
            libs = [l for l in new_libs if (l == lib or l not in line)]
            line = line.replace(f' {lib} ', ' ' + ' '.join(libs) + ' ')
            line = line.replace(f"'{lib}'", ', '.join([f"'{l}'" for l in libs]))
    return line

def replace_libs(data, libs):
    lines = data.split('\n')
    lines = [replace_libs_line(line, libs) for line in lines]
    return '\n'.join(lines)

def conan_install(args, profiles=(), filenames=None):
    if not profiles:
        return
    archs = []
    for profile in profiles:
        with tempfile.NamedTemporaryFile() as tmp:
            tmp.close()
            with tempfile.TemporaryDirectory() as tmpdir:
                args0 = list(args)
                if profile != profiles[0]:
                    args0 += ['-if', tmpdir]
                have_build = False
                args_json = []
                i = 0
                while i < len(args):
                    a = args[i]
                    if a.startswith('-') and (a.endswith(':b') or a.endswith(':build')):
                        have_build = True
                        i += 1
                        if '=' not in a:
                            i += 1
                    elif a == '-b' or a.startswith('--build'):
                        args_json.append(a)
                        i += 1
                        if '=' not in a:
                            args_json.append(args[i])
                            i += 1
                    else:
                        args_json.append(a)
                        i += 1
                if have_build:
                    run(['conan', 'install'] + args0 + ['-pr', profile], check=True)
                    with tempfile.TemporaryDirectory() as tmpdir2:
                        run(['conan', 'install'] + args_json + ['-if', tmpdir2, '--json', tmp.name, '-pr', profile], check=True)
                else:
                    run(['conan', 'install'] + args0 + ['--json', tmp.name, '-pr', profile], check=True)
                with open(tmp.name, encoding='utf-8') as f:
                    data = json.loads(f.read())
                    for i in data['installed']:
                        if len(i['packages']) > 1:
                            print('multiple packages', profile, i)
                    archs.append(data)

    # Combine packages by name and arch
    packages = {}
    for arch in archs:
        for i in arch['installed']:
            recipe = i['recipe']
            name = f"{recipe['name']}/{recipe['version']}"
            if recipe['user'] and recipe['channel']:
                name += f"@{recipe['user']}/{recipe['channel']}"
            if not i['packages']:
                continue
            assert len(i['packages']) == 1
            package = i['packages'][0]
            try:
                rootpath = package['cpp_info']['rootpath']
            except KeyError:
                pass
            else:
                if name in packages:
                    if packages[name][0] != rootpath:
                        packages[name].append(rootpath)
                else:
                    packages[name] = [rootpath]
    # Lipo packages
    pairs = []
    for name, archs in packages.items():
        if len(archs) > 1:
            fat_path = archs[0].replace('/package/', '/universal/')
            outdated = False
            try:
                mtime = os.stat(fat_path).st_mtime
                for arch in archs:
                    try:
                        if os.stat(arch).st_mtime > mtime:
                            outdated = True
                    except OSError:
                        outdated = True
            except OSError:
                pass
            if outdated:
                shutil.rmtree(fat_path)
            if not os.path.isdir(fat_path):
                lipo(fat_path, archs)
            pairs.append((archs[0], fat_path))

    # Update generator files
    if filenames is None:
        filenames = _filenames
    # TODO: build mapping from json files, smarter replace compatible with other packages.
    libs = (('opencv_core', ('opencv_core', 'tegra_hal')),)
    for f in filenames:
        if os.path.exists(f):
            replace_file(f, pairs, lambda d, libs=libs: replace_libs(d, libs))
