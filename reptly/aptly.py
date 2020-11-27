#!/usr/bin/python3
import requests
import subprocess

from typing import List, Optional


class Aptly():
    def __init__(self):
        self.mirrors = self.get_raw_list('mirror')
        self.repos = self.get_raw_list('repo')
        self.snapshots = self.get_raw_list('snapshot')
        self._publications = None
        self.keyring = None

    def run(self, *args, **kwargs):
        return subprocess.run(['aptly'] +
                              [arg for arg in args if arg], **kwargs)

    def get_raw_list(self, type):
        return self.run(type, 'list', '-raw',
                        check=True, stdout=subprocess.PIPE
                        ).stdout.decode('utf-8').split('\n')

    def publication(self, name, distribution):
        if self._publications is None:
            r = requests.get('http://localhost:8080/api/publish')
            self._publications = {}
            for publication in r.json():
                if publication['Storage'] == '':
                    target = publication['Prefix']
                else:
                    target = publication['Storage'] + ':' + publication['Prefix']
                self._publications[(target, publication['Distribution'])] = publication
        return self._publications.get((name, distribution), None)

    def snapshot_info(self, name: str):
        content = self.run('snapshot', 'show', '-with-packages', name,
                           check=True, stdout=subprocess.PIPE)
        return content.stdout.decode('utf-8')

    def snapshot_drop(self, name: str, check: bool = True):
        self.run('snapshot', 'drop', name,
                 check=check, stdout=subprocess.DEVNULL)

    def snapshot_mirror(self, snapshot: str, mirror: str):
        self.run('snapshot', 'create',
                 snapshot, 'from', 'mirror', mirror,
                 check=True, stdout=subprocess.DEVNULL)

    def snapshot_repo(self, snapshot: str, repo: str):
        self.run('snapshot', 'create',
                 snapshot, 'from', 'repo', repo,
                 check=True, stdout=subprocess.DEVNULL)

    def snapshot_diff(self, a: str, b: str):
        diff = self.run('snapshot', 'diff', a, b,
                        check=True, stdout=subprocess.PIPE).stdout
        if b'Snapshots are identical.' in diff:
            return False
        else:
            return diff.decode('utf-8')

    def snapshot_merge(self, name, sources, *, latest=False):
        args = ['snapshot', 'merge']
        if latest is True:
            args.append('-latest')
        args.append(name)
        args.extend(sources)
        self.run(*args, check=True, stdout=subprocess.DEVNULL)

    def snapshot_sources(self, name):
        snapshot_info = self.run('snapshot', 'show', name,
                                 check=True, stdout=subprocess.PIPE)
        lines = snapshot_info.stdout.decode('utf-8').split('\n')
        if 'Sources:' not in lines:
            return {}
        candidate = lines.index('Sources:') + 1
        types = {
            'snapshot': ' [snapshot]',
            'mirror': ' [repo]',
            'repo': ' [local]',
        }
        for line in lines[candidate:]:
            if not line.startswith('  '):
                break
            for label, suffix in types.items():
                if not line.endswith(suffix):
                    continue
                yield label, line[2:].rsplit(' ', 1)[0]
                break
            else:
                print(f'Ignore unknown snapshot source: {line} in ({name})')

    def mirror_update(self, name: str, *, quiet: bool = False):
        if quiet:
            extra_args = {'stdout': subprocess.DEVNULL,
                          'stderr': subprocess.PIPE}
        else:
            extra_args = {}
        self.run('mirror', 'update',
                 '-keyring=aptlykeys.gpg' if self.keyring else None,
                 name,
                 check=True, **extra_args)

    def publish(self, distro: str, target: str, content: dict, *,
                origin: Optional[str]=None,
                architectures: List[str] = None,
                acquire_by_hash: bool = True):
        args = ['publish', 'snapshot']
        args.append('-component=' + ','.join(content))
        if architectures:
            args.append('-architectures=' + ','.join(architectures)),
        args.append('-distribution=' + distro),
        if acquire_by_hash:
            args.append('-acquire-by-hash')
        if origin:
            args.append(f'-origin={origin}')
        args.extend(list(content.values()))
        args.append(target)

        self.run(*args, check=True)

    def switch(self, distro, target, snapshot):
        self.run('publish', 'switch',
                 distro, target, snapshot,
                 check=True)

    def switch_components(self, distro, target, changes):
        self.run('publish', 'switch',
                 '-component=' + ','.join(changes.keys()),
                 distro, target, *changes.values(),
                 check=True)
