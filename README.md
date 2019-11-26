Reptly: reprepro like usage of aptly 
====================================

[Aptly](https://aptly.info) is a powerful tool to manage and publish [Debian Packages (DEB)](https://wiki.debian.org/deb). Sadly it isn't easy to use. It is a toolkit and allows almost all workflows and usecases. Common workflows like update everything and publish the result require multiple steps.
This projects (**reptly**) provides a wrapper around Aptly to describe simply workflows as configuration file and execute them with a simple command.
The tool is to combine Reprepro's easy to use commands like update, with the features of Aptly.

**Reptly** is primarily designed for humans to make their repo management easier. Integration into tools should probably use aptly directly as they already use scripts/automatication.


## Goals

* Built up-on Aptly's snaphots (take snapshots of mirrors and repos)
* To not limit configuration abouts around mirrors, repos, snapshots
* Easily manage snapshot merges (combine different repos / mirrors): a simple command should be enough
* Interactive update approval / rollback
* Document / persist which publication targets exists and which software they should contain
* Easily downgrade specific updates or delay updates (one major update of a specific software)
* Notifications (e.g. cron) to information about new available updates


## Example

```yaml
keyring: special-keyring-for-mirror-update.gpg  # optional

publish:  # list of different publications
  - # internal identifier: used e.g. for snapshot names
    # reptly accept such names to only work on a subset of repos
    alias: 'mon-xenial'
    # Where to publish the data? prefix for aptly publish
    destination: s3:apt:mon
    # As what destribution should the data be published?
    distribution: xenial
    # What componet to use? Default is 'main'
    component: main

    # Which data to publish?
    # individual resources can be referenced directly
    source: !mirror software-a
       # run mirror update
       # snapshot result
       # publish such a snapshot
    source: !repo software-b
       # take snapshots of repo and publish one of them
    source: !snapshot name
       # publish a fixed name snapshot (designed for legacy data or temporary manually fixes)
    source: !empty  # publish an empty snapshot (no packages at all)

    # multiple sources can be combined automatically:
    # snapshots of each type will be merged together
    source:
    - !mirror software-a
    - !mirror libc
    - !repo software-b
    - !snapshot software-c

# multi component deployments:
# keep in mind aptly does not supported changes the list
# of components for published stuff (bug )
  - alias: os-bionic
    destination: s3:apt:openstack
    distribution: bionic
    components:
      main: !snapshot.merge  # merge multipe snapshots together
        name: 'os-bionic'  # how to name merged snapshots
        sources:
          - !repo telegraf
          - !repo backports-bionic
          - !mirror cephmimic-bionic
      openstack-queens: !mirror openstack-queens  # publish a mirror directly
      openstack-stein: !snapshot empty # create component, but leave it empty for now
```

## Requirements

The scripts both execute the aptly binary (primarily for `mirror update`) to get feedback about what happens for longer operations. It also calls the Aptly API as it provides information not available or difficult to parse with aptly commands itself.

For now it does not start the API itself. Although this is planed in the feature.

The script is implemented in Python. The goal is to limit dependencies to a absolute minimum. It still uses `yaml` as configuration file and may use `prompt_toolkit` for easy to use CLI questions.


## Usage

This is a very brief explanation. Reference the usage of `reptly` for the exact set of commands and arguments.

### Managing mirrors and repos

Use the normal command to created, edit mirrors and repos. Afterwards you can reference them in the reptly config.

### Check for updates

Call `reptly update` to download new available updates from mirrors (`aptly mirror update`). Repos are currently not updated but a new snapshot is created if they have changed. Automatic `repo include` call should be added later one.

### Publishing changes

Run `reptly publish`. It will ask you change changes are available and whether you want to publish them.

### Shorthands

`reptly run` is a shorthand for `reptly update` and `reptly pubish`.

All commands take an optional filter to limit there operation. Use the internal `alias` identifier to operate on specific publish targets and their sources only. Wildcards matches ala `dev*` are supported, too. 

## Update notifications

`reptly --cron` provides a easy non-interactive mode to automatically check for updates. Output is only created on changes or errors.

Use `reptly --cron update` to download new changes from mirrors.

Run `reptly --cron publish` to print available outstanding changes.


## Testing

There are no test at the moment. This should change at samepoint. The software interacts heavily with aptly so it is harder to write tests.


## Contributing

1. Fork it
2. Create your feature branch (git checkout -b my-new-feature)
3. Add tests for your feature.
4. Add your feature.
5. Commit your changes (git commit -am 'Add some feature')
6. Push to the branch (git push origin my-new-feature)
7. Create new Pull Request

## License

LGPL License

Copyright (c) 2018-2019, Malte Swart
