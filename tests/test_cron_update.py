class Namespace():
    def __init__(self, target):
        self.target = target
        self.cron = True


def test_no_output_on_no_changes(app, aptly, cronui, capfd):
    app.ui = cronui
    aptly.register_mirror('sw1', snapshots=[1])
    aptly.register_mirror('sw2', snapshots=[2, 3])
    aptly.register_repo('pkgs', snapshots=[8])
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
        - !mirror sw1
        - !mirror sw2
      - alias: 'test2-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !repo pkgs''')

    aptly.schedule('mirror_update', 'sw1', True)
    aptly.schedule('snapshot_mirror', 'sw1+r2', 'sw1')
    aptly.schedule('snapshot_diff', 'sw1+r1', 'sw1+r2', ret=False)
    aptly.schedule('snapshot_drop', 'sw1+r2', True)
    aptly.schedule('mirror_update', 'sw2', True)
    aptly.schedule('snapshot_mirror', 'sw2+r4', 'sw2')
    aptly.schedule('snapshot_diff', 'sw2+r3', 'sw2+r4', ret=False)
    aptly.schedule('snapshot_drop', 'sw2+r4', True)
    aptly.schedule('snapshot_repo', 'pkgs+r9', 'pkgs')
    aptly.schedule('snapshot_diff', 'pkgs+r8', 'pkgs+r9', ret=False)
    aptly.schedule('snapshot_drop', 'pkgs+r9', True)

    app.exec_update(Namespace([]))
    assert aptly.pending_ops == []

    out, err = capfd.readouterr()
    assert out == ''
    assert err == ''


def test_only_output_of_changes(app, aptly, cronui, capfd):
    app.ui = cronui
    app.aptly.register_mirror('sw1', snapshots=[1])
    app.aptly.register_mirror('sw2', snapshots=[2, 3])
    app.aptly.register_repo('pkgs', snapshots=[8])
    app.load('''publish:
      - alias: 'test-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source:
        - !mirror sw1
        - !mirror sw2
      - alias: 'test2-distro'
        destination: s3:apt:mon
        distribution: distro
        component: main
        source: !repo pkgs''')

    aptly.schedule('mirror_update', 'sw1', True)
    aptly.schedule('snapshot_mirror', 'sw1+r2', 'sw1')
    aptly.schedule('snapshot_diff', 'sw1+r1', 'sw1+r2', ret=False)
    aptly.schedule('snapshot_drop', 'sw1+r2', True)
    aptly.schedule('mirror_update', 'sw2', True)
    aptly.schedule('snapshot_mirror', 'sw2+r4', 'sw2')
    aptly.schedule('snapshot_diff', 'sw2+r3', 'sw2+r4', ret='Important diff')
    aptly.schedule('snapshot_repo', 'pkgs+r9', 'pkgs')
    aptly.schedule('snapshot_diff', 'pkgs+r8', 'pkgs+r9', ret=False)
    aptly.schedule('snapshot_drop', 'pkgs+r9', True)

    app.exec_update(Namespace([]))
    assert aptly.pending_ops == []

    out, err = capfd.readouterr()
    assert 'Important diff' in out
    assert 'sw2' in out
    assert 'sw1' not in out
    assert 'pkgs' not in out
    assert err == ''
