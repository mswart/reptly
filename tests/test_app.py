

def test_configure_keyring(app, aptly):
    app.load('''keyring: test
publish: []''')

    assert aptly.keyring == 'test'
    assert aptly.pending_ops == []
