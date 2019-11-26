class Namespace():
    def __init__(self, target):
        self.target = target
        self.cron = True


# mirror


def test_skip_other_updates(app, aptly):
    app.aptly.mirrors.append('test')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    app.exec_update(Namespace(['other']))
    assert aptly.pending_ops == []


def test_update_mirror_initially(app, aptly):
    app.aptly.mirrors.append('test')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    aptly.schedule('mirror_update', 'test', True)
    aptly.schedule('snapshot_mirror', 'test+r1', 'test')
    aptly.schedule('snapshot_info', 'test+r1', ret='Empty')

    app.exec_update(Namespace(['test']))
    assert aptly.pending_ops == []


def test_update_mirror_without_diff(app, aptly):
    aptly.mirrors.append('test')
    aptly.snapshots.append('test+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    aptly.schedule('mirror_update', 'test', True)
    aptly.schedule('snapshot_mirror', 'test+r2', 'test')
    aptly.schedule('snapshot_diff', 'test+r1', 'test+r2', ret=False)
    aptly.schedule('snapshot_drop', 'test+r2', True, ret=False)

    app.exec_update(Namespace(['test']))
    assert aptly.pending_ops == []


def test_update_mirror_with_diff(app, aptly):
    aptly.mirrors.append('test')
    aptly.snapshots.append('test+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !mirror test''')

    aptly.schedule('mirror_update', 'test', True)
    aptly.schedule('snapshot_mirror', 'test+r2', 'test')
    aptly.schedule('snapshot_diff', 'test+r1', 'test+r2', ret='Diff!')

    app.exec_update(Namespace(['test']))
    assert aptly.pending_ops == []


# repo


def test_skip_other_repo_update(app, aptly):
    aptly.repos.append('test')
    aptly.snapshots.append('test+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !repo test''')

    app.exec_update(Namespace(['other']))
    assert aptly.pending_ops == []


def test_update_repo_without_diff(app, aptly):
    aptly.repos.append('test')
    aptly.snapshots.append('test+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !repo test''')

    aptly.schedule('snapshot_repo', 'test+r2', 'test')
    aptly.schedule('snapshot_diff', 'test+r1', 'test+r2', ret=False)
    aptly.schedule('snapshot_drop', 'test+r2', True, ret=False)

    app.exec_update(Namespace(['test']))
    assert aptly.pending_ops == []


def test_update_repo_with_diff(app, aptly):
    aptly.repos.append('test')
    aptly.snapshots.append('test+r1')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !repo test''')

    aptly.schedule('snapshot_repo', 'test+r2', 'test')
    aptly.schedule('snapshot_diff', 'test+r1', 'test+r2', ret='Diff!')

    app.exec_update(Namespace(['test']))
    assert aptly.pending_ops == []
