import os
from typing import List
import sys

import pytest


parent = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if os.path.isdir(os.path.join(parent, 'reptly')):
    sys.path.insert(0, parent)


from reptly.app import App
from reptly.domain import Mirror, Repo
from reptly.ui import CronUI


class Testly():
    def __init__(self):
        self.mirrors = []
        self.repos = []
        self.snapshots = []
        self.publications = {}
        self.pending_ops = []

    def register_snapshot(self, name):
        self.snapshots.append(name)

    def register_mirror(self, name: str, *, snapshots: List[int]=[]):
        self.mirrors.append(name)
        for snapshot in snapshots:
            self.snapshots.append(f'{name}+r{snapshot}')

    def register_repo(self, name: str, snapshots: List[int]=[]):
        self.repos.append(name)
        for snapshot in snapshots:
            self.snapshots.append(f'{name}+r{snapshot}')

    def schedule(self, *args, ret=None):
        self.pending_ops.append((args, ret))

    def register_publication(self, name, distribution, **components):
        self.publications[(name, distribution)] = {
            'Sources': [
                {'Component': comp, 'Name': snap}
                for comp, snap in components.items()
            ],
        }

    def run(self, *args):
        op, ret = self.pending_ops.pop(0)
        assert op == args
        return ret

    def publication(self, name, distribution):
        return self.publications.get((name, distribution), None)

    def snapshot_info(self, name: str):
        return self.run('snapshot_info', name)

    def snapshot_drop(self, name: str, check: bool = True):
        return self.run('snapshot_drop', name, check)

    def snapshot_mirror(self, snapshot: str, mirror: str):
        return self.run('snapshot_mirror', snapshot, mirror)

    def snapshot_repo(self, snapshot: str, repo: str):
        return self.run('snapshot_repo', snapshot, repo)

    def snapshot_diff(self, a: str, b: str):
        return self.run('snapshot_diff', a, b)

    def snapshot_merge(self, name, sources, *, latest=False):
        return self.run('snapshot_merge', name, latest, *sources)

    def snapshot_sources(self, name: str):
        return self.run('snapshot_sources', name)

    def mirror_update(self, name: str, *, quiet: bool = False):
        return self.run('mirror_update', name, quiet)

    def publish(self, distro: str, target: str, content: dict, *,
                architectures: List[str] = None,
                acquire_by_hash: bool = True):
        self.run('publish', target, distro, content, architectures,
                 acquire_by_hash)

    def switch(self, distro, target, snapshot):
        self.run('switch', distro, target, snapshot)

    def switch_components(self, distro, target, changes):
        self.run('switch_components', distro, target, changes)


class TestUI():
    def __init__(self):
        self.decisions = {}

    def decide(self, action, object, decision):
        self.decisions[(action, object)] = decision

    def act(self, name, arg, yes, no):
        decision = self.decisions.get((name, arg), True)
        print((name, arg, decision, yes, no))
        if decision is True:
            return yes
        else:
            return no

    def mirror_update(self, mirror, action):
        action(quiet=True)

    def include_snapshot(self, snapshot, info):
        return self.act('include_snapshot', snapshot.name, snapshot, False)

    def update_snapshot(self, current, proposed, *, diff, source):
        return self.act('update_snapshot', (current.name, proposed.name),
                        proposed, current)

    def remove_snapshot(self, current, info):
        return self.act('remove_snapshot', current.name,
                        False, current)

    def prepare_switch(self, publish, component):
        self.current_switch = (publish, component)

    def skip_switch(self):
        pass

    def switch(self, diff, *, target, distribution, component):
        return self.act('switch', (target, distribution, component),
                        True, False)


@pytest.fixture
def app():
    ui = TestUI()
    aptly = Testly()
    app = App(aptly, ui)
    Mirror.mirrors = {}
    Repo.repos = {}

    return app


@pytest.fixture
def aptly(app):
    return app.aptly


@pytest.fixture
def cronui():
    return CronUI()
