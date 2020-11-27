import pytest


class Namespace():
    def __init__(self, target):
        self.target = target
        self.cron = True


# single


def test_skip_other_publish(app, aptly):
    aptly.register_mirror('test')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    app.exec_publish(Namespace(['other-name']))
    assert aptly.pending_ops == []


@pytest.mark.xfail
def test_publish_single_newly_without_snapshots(app, aptly):
    aptly.register_mirror('test')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_single_newly_with_snapshots(app, aptly):
    aptly.register_mirror('test', snapshots=[1])
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    aptly.schedule('publish', 's3:apt:mon', 'distro', None, {'main': 'test+r1'},
                   [], True)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_single_newly_with_origin(app, aptly):
    aptly.register_mirror('test', snapshots=[1])
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        origin: cloud
        source: !mirror test''')

    aptly.schedule('publish', 's3:apt:mon', 'distro', 'cloud', {'main': 'test+r1'},
                   [], True)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_single_switch_with_change(app, aptly):
    aptly.register_mirror('test', snapshots=[1, 2])
    aptly.register_publication('s3:apt:mon', 'distro', main='test+r1')

    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    aptly.schedule('snapshot_diff', 'test+r1', 'test+r2', ret='Diff!')
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test+r2')
    aptly.schedule('snapshot_drop', 'test+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


# single snapshot

def test_publish_fixed_snapshot_newly(app, aptly):
    aptly.register_mirror('test')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !snapshot extern-managed''')

    aptly.schedule('publish', 's3:apt:mon', 'distro', None, {'main': 'extern-managed'},
                   [], True)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_update_fixed_snapshot(app, aptly):
    aptly.register_mirror('test', snapshots=[1])
    aptly.register_publication('s3:apt:mon', 'distro', main='extern-managed')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !snapshot extern-managed2''')

    aptly.schedule('snapshot_diff', 'extern-managed', 'extern-managed2', ret='Diff!')

    aptly.schedule('switch', 'distro', 's3:apt:mon', 'extern-managed2')

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


# merge

def test_publish_merge_newly(app, aptly):
    aptly.register_mirror('software1')
    aptly.register_mirror('software2')
    aptly.register_repo('test1')
    aptly.register_snapshot('test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo test1''')

    aptly.schedule('publish', 's3:apt:mon', 'distro', None,
                   {'main': 'test-distro+r1'}, [], True)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_switch_with_diff(app, aptly):
    aptly.register_mirror('software1', snapshots=[1])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo pkgs1''')

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software1+r1', 'software2+r2', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret='D!')
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_switch_with_mirror_diff_only(app, aptly):
    aptly.register_mirror('software1', snapshots=[1])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo pkgs1''')

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software1+r1', 'software2+r2', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret=False)
    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_sources', 'test-distro+r2', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r2'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_switch_diffless_changes(app, aptly):
    aptly.register_mirror('software1', snapshots=[1])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo pkgs1''')

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret=False)
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software1+r1', 'software2+r2', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret=False)
    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_sources', 'test-distro+r2', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r2'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_include_without_upgrade_other(app, aptly):
    aptly.register_mirror('software1', snapshots=[1])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo pkgs1''')

    app.ui.decide('update_snapshot', ('software2+r1', 'software2+r2'), False)

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_info', 'software1+r1', ret='NEW!')
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software1+r1', 'software2+r1', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret='NEW!')
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_remove_without_upgrade_other(app, aptly):
    aptly.register_mirror('software1', snapshots=[1])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software2
          - !repo pkgs1''')

    app.ui.decide('update_snapshot', ('software2+r1', 'software2+r2'), False)

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_info', 'software1+r1', ret='NEW!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software2+r1', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret='NEW!')
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_skip_remove_upgrade_other(app, aptly):
    aptly.register_mirror('software1', snapshots=[1])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software2
          - !repo pkgs1''')

    app.ui.decide('remove_snapshot', 'software1+r1', False)

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_info', 'software1+r1', ret='NEW!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software2+r2', 'pkgs1+r1', 'software1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret='NEW!')
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_upgrade_only_one(app, aptly):
    aptly.register_mirror('software1', snapshots=[1, 2])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo pkgs1''')

    app.ui.decide('update_snapshot', ('software1+r1', 'software1+r2'), False)
    app.ui.decide('update_snapshot', ('software2+r1', 'software2+r2'), True)

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software1+r1', 'software1+r2', ret='D!')
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software1+r1', 'software2+r2', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret='NEW!')
    aptly.schedule('switch', 'distro', 's3:apt:mon', 'test-distro+r2')
    aptly.schedule('snapshot_drop', 'test-distro+r1', False)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_merge_cancel_upgrade(app, aptly):
    aptly.register_mirror('software1', snapshots=[1, 2])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
          - !mirror software1
          - !mirror software2
          - !repo pkgs1''')
    app.ui.decide('switch', ('s3:apt:mon', 'distro', 'main'), False)

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r1'),
        ('snapshot', 'pkgs1+r1'),
    ])
    aptly.schedule('snapshot_diff', 'software1+r1', 'software1+r2', ret='D!')
    aptly.schedule('snapshot_diff', 'software2+r1', 'software2+r2', ret='D!')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True,
                   'software1+r2', 'software2+r2', 'pkgs1+r1')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2', ret='Diff')
    aptly.schedule('snapshot_drop', 'test-distro+r2', True)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


# multiple components


def test_publish_components_initially(app, aptly):
    aptly.register_mirror('software1', snapshots=[1, 2])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro-main+r1')
    # aptly.register_publication('s3:apt:mon', 'distro', main='pkgs+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        components:
          main: !snapshot.merge
            name: test-distro-main
            sources:
              - !mirror software1
              - !mirror software2
          extra: !repo pkgs1''')
    app.ui.decide('switch', ('s3:apt:mon', 'distro', 'main'), False)

    aptly.schedule('publish', 's3:apt:mon', 'distro', None, {
            'extra': 'pkgs1+r1',
            'main': 'test-distro-main+r1'
        }, [], True)

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []


def test_publish_components_update_one(app, aptly):
    aptly.register_mirror('software1', snapshots=[1, 2])
    aptly.register_mirror('software2', snapshots=[1, 2])
    aptly.register_repo('pkgs1', snapshots=[1])
    aptly.register_snapshot('test-distro-main+r1')
    aptly.register_publication('s3:apt:mon', 'distro',
                               main='test-distro-main+r1',
                               extra='pkgs1+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        components:
          main: !snapshot.merge
            name: test-distro-main
            sources:
              - !mirror software1
              - !mirror software2
          extra: !repo pkgs1''')
    app.ui.decide('switch', ('s3:apt:mon', 'distro', 'main'), True)

    aptly.schedule('snapshot_sources', 'test-distro-main+r1', ret=[
        ('snapshot', 'software1+r1'),
        ('snapshot', 'software2+r2'),
    ])
    aptly.schedule('snapshot_diff', 'software1+r1', 'software1+r2', ret='D!')
    aptly.schedule('snapshot_merge', 'test-distro-main+r2', True,
                   'software1+r2', 'software2+r2')
    aptly.schedule('snapshot_diff', 'test-distro-main+r1',
                   'test-distro-main+r2', ret='D!')
    aptly.schedule('switch_components', 'distro', 's3:apt:mon',
                   {'main': 'test-distro-main+r2'})

    app.exec_publish(Namespace(['test-distro']))
    assert aptly.pending_ops == []
