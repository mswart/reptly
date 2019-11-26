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

    app.exec_run(Namespace(['other']))
    assert aptly.pending_ops == []


def test_update_all_referenced_mirrors_and_publish_initially(app, aptly):
    aptly.register_mirror('sw1')
    aptly.register_mirror('sw2')
    aptly.register_mirror('sw3')
    aptly.register_mirror('sw4')
    app.load('''publish:
      - alias: 'publish-name'
        destination: s3:apt:mon
        distribution: distro
        components:
          main: !mirror sw1
          extra: !snapshot.merge
            name: comp-name
            sources:
              - !mirror sw2
              - !mirror sw3
      - alias: 'other-test'
        destination: s3:apt:asdf
        distribution: dist2
        source: !mirror sw4''')

    aptly.schedule('mirror_update', 'sw1', True)
    aptly.schedule('snapshot_mirror', 'sw1+r1', 'sw1')
    aptly.schedule('snapshot_info', 'sw1+r1', ret='Empty')

    aptly.schedule('mirror_update', 'sw2', True)
    aptly.schedule('snapshot_mirror', 'sw2+r1', 'sw2')
    aptly.schedule('snapshot_info', 'sw2+r1', ret='Empty')

    aptly.schedule('mirror_update', 'sw3', True)
    aptly.schedule('snapshot_mirror', 'sw3+r1', 'sw3')
    aptly.schedule('snapshot_info', 'sw3+r1', ret='Empty')

    aptly.schedule('snapshot_merge', 'comp-name+r1', True, 'sw2+r1', 'sw3+r1')
    aptly.schedule('publish', 's3:apt:mon', 'distro',
                   {'extra': 'comp-name+r1', 'main': 'sw1+r1'}, [], True)

    app.exec_run(Namespace(['publish-name']))
    assert aptly.pending_ops == []
