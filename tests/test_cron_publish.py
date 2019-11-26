class Namespace():
    def __init__(self, target):
        self.target = target
        self.cron = True


# mirror


def test_no_output_on_no_changes(app, aptly, cronui, capfd):
    app.ui = cronui
    aptly.register_mirror('sw1', snapshots=[1])
    aptly.register_mirror('sw2', snapshots=[2, 3])
    aptly.register_repo('pkgs', snapshots=[8])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    aptly.register_publication('s3:apt:man', 'distro', main='pkgs+r8')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
        - !mirror sw1
        - !mirror sw2
      - alias: 'test2-distro'
        destination: s3:apt:man
        distribution: distro
        component: main
        source: !repo pkgs''')

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'sw1+r1'),
        ('snapshot', 'sw2+r3'),
    ])
    aptly.schedule('snapshot_merge', 'test-distro+r2', True, 'sw1+r1', 'sw2+r3')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2',
                   ret=False)

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'sw1+r1'),
        ('snapshot', 'sw2+r3'),
    ])
    aptly.schedule('snapshot_sources', 'test-distro+r2', ret=[
        ('snapshot', 'sw1+r1'),
        ('snapshot', 'sw2+r3'),
    ])
    aptly.schedule('snapshot_drop', 'test-distro+r2', True)

    app.exec_publish(Namespace([]))
    assert aptly.pending_ops == []

    out, err = capfd.readouterr()
    assert out == ''
    assert err == ''


def test_only_output_of_changes(app, aptly, cronui, capfd):
    app.ui = cronui
    aptly.register_mirror('sw1', snapshots=[1])
    aptly.register_mirror('sw2', snapshots=[2, 3])
    aptly.register_repo('pkgs', snapshots=[8])
    aptly.register_snapshot('test-distro+r1')
    aptly.register_publication('s3:apt:mon', 'distro', main='test-distro+r1')
    aptly.register_publication('s3:apt:man', 'distro', main='pkgs+r8')
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
        - !mirror sw1
        - !mirror sw2
      - alias: 'test2-distro'
        destination: s3:apt:man
        distribution: distro
        component: main
        source: !repo pkgs''')

    aptly.schedule('snapshot_sources', 'test-distro+r1', ret=[
        ('snapshot', 'sw2+r2'),
        ('snapshot', 'sw3+r1'),
    ])
    aptly.schedule('snapshot_info', 'sw1+r1', ret='New Snapshot')
    aptly.schedule('snapshot_diff', 'sw2+r2', 'sw2+r3', ret='Updated Snapshot')
    aptly.schedule('snapshot_info', 'sw3+r1', ret='Removed Snapshot')
    aptly.schedule('snapshot_merge', 'test-distro+r2', True, 'sw1+r1', 'sw2+r3')
    aptly.schedule('snapshot_diff', 'test-distro+r1', 'test-distro+r2',
                   ret='Overall Diff')
    aptly.schedule('snapshot_drop', 'test-distro+r2', True)

    app.exec_publish(Namespace([]))
    assert aptly.pending_ops == []

    out, err = capfd.readouterr()
    assert 'Overall Diff' in out
    assert 'test-distro/main' in out
    assert 'test2-distro' not in out
    assert err == ''
