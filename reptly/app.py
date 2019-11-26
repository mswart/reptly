#!/usr/bin/python3.8
import fnmatch
import functools
import typing

import yaml

from reptly.domain import Publish, Merge, Mirror, Repo, FixSnapshot


class ConfigLoader(yaml.Loader):
    pass


def construct_scalar_type(type, loader, node):
    value = loader.construct_scalar(node)
    return type.byname(value)


def construct_merge(loader, node):
    value = loader.construct_mapping(node)
    return Merge(**value)


for cls in [Mirror, Repo, FixSnapshot]:
    ConfigLoader.add_constructor(
        cls.constructor,
        functools.partial(construct_scalar_type, cls))
ConfigLoader.add_constructor('!snapshot.merge', construct_merge)


class App():
    def __init__(self, aptly, ui):
        self.aptly = aptly
        self.ui = ui
        self.publications = []

    def load(self, conf: typing.TextIO):
        data = yaml.load(conf, Loader=ConfigLoader)

        if data.get('keyring'):
            self.aptly.keyring = data['keyring']

        for pub in data['publish']:
            prefix = pub.pop('destination')
            dist = pub.pop('distribution')
            self.publications.append(Publish(prefix, dist, pub))

        for p in self.publications:
            p.link(self)

    def exec_update(self, args):
        filter = args.target or ['*']

        for obj in list(Mirror.mirrors.values()) + list(Repo.repos.values()):
            if not any(fnmatch.fnmatch(obj.name, f) for f in filter):
                continue
            update = obj.update(args)
            if update:
                if args.cron:
                    print(obj.name)
                    print('-'*len(obj.name))
                else:
                    print()
                print(update.diff)

    def exec_publish(self, args):
        filter = args.target or ['*']

        for p in self.publications:
            if not any(fnmatch.fnmatch(p.alias, f) for f in filter):
                continue
            p.publish(args)

    def exec_run(self, args):
        filter = args.target or ['*']

        for p in self.publications:
            if not any(fnmatch.fnmatch(p.alias, f) for f in filter):
                continue
            for update in p.update_all(args):
                print(update)
                print(update.diff)
            p.publish(args)
