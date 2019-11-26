import collections
from functools import partial
import re

Diff = collections.namedtuple('Diff', ('diff', 'old', 'new'))


def snapshot_sources(aptly, snapshot):
    sources = {}
    for type, name in aptly.snapshot_sources(snapshot):
        if type != 'snapshot':
            continue
        alias, rev = name.split('+r')
        sources[alias] = SnapshotContentMixin.Snapshot(name, int(rev))
    return sources


class SnapshotContentMixin():
    class Snapshot():
        def __init__(self, name, rev, *, temporary=False):
            self.name = name
            self.rev = rev
            self.temporary = temporary

        def delete(self):
            if not self.temporary:
                return
            self.temporary.snapshot_drop(self.name)

        def __eq__(self, other):
            if type(other) != type(self):
                raise NotImplementedError()
            return self.name == other.name and self.rev == other.rev

        def __repr__(self):
            return f'Snapshot({self.name}, {self.rev}, temporary={self.temporary})'

    def publication_candidate(self, _published):
        return self.current

    def _extract_own_snapshots(self):
        self.snapshots = []
        for s in self.aptly.snapshots:
            if not s.startswith(self.name + '+r'):
                continue
            self.snapshots.append(self.Snapshot(s, int(s.split('+r')[1])))
        self.snapshots = sorted(self.snapshots,
                                key=lambda s: s.rev)

    @property
    def current(self):
        return max(
            self.snapshots,
            key=lambda s: s.rev,
            default=None
        )

    def _new_snapshot(self):
        current = self.current or self.Snapshot(None, 0)
        new = self.Snapshot(
            f'{self.name}+r{current.rev + 1}',
            current.rev + 1,
            temporary=self.aptly
        )
        return current, new

    def _snapshot_new(self, current, new):
        ''' Check whether the newly created snapshot is
            different from the current one.
            New snapshot is dropped if there is not
            changes.
        '''
        # 3. compare for changes
        if current.rev == 0:  # we have not older snapshots
            self.snapshots.append(new)
            return Diff(self.aptly.snapshot_info(new.name), current, new)
        diff = self.aptly.snapshot_diff(current.name, new.name)
        if not diff:
            new.delete()
            return False
        else:
            new.temporary = False
        self.snapshots.append(new)
        return Diff(diff, current, new)

    def update_all(self, args):
        u = self.update(args)
        if u:
            yield u


class Mirror(SnapshotContentMixin):
    constructor = '!mirror'
    mirrors = {}

    def __init__(self, name):
        self.name = name
        self.snapshots = []

    def __repr__(self):
        return 'Mirror({self.name})'.format(self=self)

    def link(self, app):
        self.aptly = app.aptly
        self.ui = app.ui
        assert self.name in self.aptly.mirrors, 'Unknown mirror ' + self.name
        self._extract_own_snapshots()
        return self

    def update(self, args):
        # 1. update mirror
        self.ui.mirror_update(self,
                              partial(self.aptly.mirror_update, self.name))
        current, new = self._new_snapshot()
        self.aptly.snapshot_mirror(new.name, self.name)
        return self._snapshot_new(current, new)

    @classmethod
    def byname(cls, name):
        if name not in cls.mirrors:
            cls.mirrors[name] = Mirror(name)
        return cls.mirrors[name]


class Repo(SnapshotContentMixin):
    constructor = '!repo'
    repos = {}

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'Repo({self.name})'.format(self=self)

    def link(self, app):
        self.aptly = app.aptly
        assert self.name in self.aptly.repos, f'Unknown repo {self.name}'
        self._extract_own_snapshots()
        return self

    def update(self, args):
        current, new = self._new_snapshot()
        self.aptly.snapshot_repo(new.name, self.name)
        return self._snapshot_new(current, new)

    @classmethod
    def byname(cls, name):
        if name not in cls.repos:
            cls.repos[name] = Repo(name)
        return cls.repos[name]


class FixSnapshot(SnapshotContentMixin):
    constructor = '!snapshot'
    snapshots = {}

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return f'Snapshot({self.name})'

    def link(self, _app):
        return self

    @property
    def current(self):
        return self.Snapshot(self.name, 0)

    @classmethod
    def byname(cls, name):
        if name not in cls.snapshots:
            cls.snapshots[name] = FixSnapshot(name)
        return cls.snapshots.get(name, name)


class Merge(SnapshotContentMixin):
    constructor = '!merge'

    def __init__(self, name, sources, *, latest=True):
        self.name = name
        self.sources = sources
        self.latest = latest

    def link(self, app):
        for source in self.sources:
            source.link(app)
        self.aptly = app.aptly
        self.ui = app.ui
        self._extract_own_snapshots()
        return self

    def update_all(self, args):
        for source in self.sources:
            yield from source.update_all(args)

    def __repr__(self):
        return 'Merge({self.name}, {self.sources!r}, latest={self.latest})'.format(self=self)

    @property
    def current(self):
        c = super().current
        if c:
            return c
        new = self.Snapshot(
            f'{self.name}+r{1}',
            1,
            temporary=self.aptly
        )
        self.aptly.snapshot_merge(new.name,
                                  [s.current.name for s in self.sources],
                                  latest=self.latest)
        return new

    def publication_candidate(self, published_snapshot):
        published_sources = snapshot_sources(self.aptly, published_snapshot)
        merge = []
        for source in self.sources:
            published = published_sources.pop(source.name, None)
            newest = source.current
            if not published:
                info = self.aptly.snapshot_info(newest.name)
                answer = self.ui.include_snapshot(newest, info)
                if answer:
                    merge.append(answer)
                    continue
            if published.rev == newest.rev:
                merge.append(newest)
                continue
            diff = self.aptly.snapshot_diff(published.name, newest.name)
            if not diff:
                merge.append(newest)
                continue
            answer = self.ui.update_snapshot(published, newest,
                                             diff=diff, source=source)
            if answer:
                merge.append(answer)
            else:
                return None
        for snapshot in published_sources.values():
            info = self.aptly.snapshot_info(snapshot.name)
            answer = self.ui.remove_snapshot(snapshot, info)
            if answer:
                merge.append(answer)
        _, new = self._new_snapshot()
        self.aptly.snapshot_merge(new.name, [s.name for s in merge],
                                  latest=self.latest)
        return new


class Publish():
    def __init__(self, target, distribution, config):
        self.target = target
        self.distribution = distribution
        self.architectures = []
        self.alias = config.pop('alias')

        if 'components' in config:
            assert 'component' not in config, \
                'component and components are mutive exclusiv'
            assert 'source' not in config, \
                'source is only for component (not for components)'
            self.components = config.pop('components')
        else:
            component = config.get('component', 'main')
            assert 'source' in config, \
                'source is required without components'
            source = config.pop('source')
            if type(source) is list:
                source = Merge(self.alias, source)
            self.components = {component: source}

    def link(self, app):
        for source in self.components.values():
            source.link(app)
        self.aptly = app.aptly
        self.ui = app.ui

    def _define_switch(self, component, publishedSnapshot):
        self.ui.prepare_switch(self, component)
        source = self.components[component]
        candidate = source.publication_candidate(publishedSnapshot)
        if not candidate:
            self.ui.skip_switch()
            return False
        if publishedSnapshot == candidate.name:  # same snapshot
            self.ui.skip_switch()
            candidate.delete()
            return False
        # 1. print diff to user:
        diff = self.aptly.snapshot_diff(publishedSnapshot, candidate.name)
        if not diff:
            old = snapshot_sources(self.aptly, publishedSnapshot)
            new = snapshot_sources(self.aptly, candidate.name)
            assert old == old
            assert new == new
            self.ui.skip_switch()
            if old != new:
                return Diff(diff, publishedSnapshot, candidate)
            candidate.delete()
            return None
        if self.ui.switch(diff,
                          target=self.target,
                          distribution=self.distribution,
                          component=component):
            return Diff(diff, publishedSnapshot, candidate)
        else:
            candidate.delete()
            return False

    def _publish_initially(self):
        self.aptly.publish(
            self.distribution, self.target,
            {c: s.current.name for c, s in self.components.items()},
            architectures=self.architectures,
            acquire_by_hash=True
        )

    def _publish_component(self, component, publishedSnapshot):
        wanted = self._define_switch(component, publishedSnapshot)
        if not wanted:
            return

        self.aptly.switch(self.distribution, self.target, wanted.new.name)
        if re.match('.*\+r[0-9]+$', wanted.old):
            self.aptly.snapshot_drop(wanted.old, check=False)

    def _publish_components(self, publishedSnapshots):
        switching_components = {}
        for component, snapshot in self.components.items():
            wanted = self._define_switch(component,
                                         publishedSnapshots[component])
            if wanted:
                switching_components[component] = wanted.new.name

        if switching_components:
            self.aptly.switch_components(self.distribution, self.target,
                                         switching_components)

    def publish(self, args):
        p = self.aptly.publication(self.target, self.distribution)
        if p is None:  # first publication:
            return self._publish_initially()
        currentSnapshots = {s['Component']: s['Name'] for s in p['Sources']}
        assert set(currentSnapshots) == set(self.components), \
            'aptly for now does not support changing the list of components' \
            ': republish the repository!'

        if len(self.components) < 2:
            self._publish_component(*currentSnapshots.popitem())
        else:
            self._publish_components(currentSnapshots)

    def update_all(self, args):
        for source in self.components.values():
            yield from source.update_all(args)
