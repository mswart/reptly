import functools
import sys

from prompt_toolkit.shortcuts import create_prompt_application, run_application
from prompt_toolkit.key_binding.registry import Registry
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.keys import Keys
from prompt_toolkit.styles import style_from_dict
from pygments.token import Token


def select(message, *options):
    """
    Display a confirmation prompt.
    """
    styling = style_from_dict({
        Token.Key: 'bold',
        Token.DefaultKey: 'bold underline',
    })

    def _get_tokens(cli):
        yield (Token, message + ': ')
        for i, option in enumerate(options):
            if i:
                yield (Token, ', ')
            if option.default:
                yield (Token.DefaultKey, option.caption[0].upper())
            else:
                yield (Token.Key, option.caption[0].upper())
            yield (Token.Caption, option.caption[1:])
        yield (Token, '? ')

    def _event(option, event):
        event.cli.buffers[DEFAULT_BUFFER].text = option.output
        event.cli.set_return_value(option.value)

    registry = Registry()

    for option in options:
        handler = functools.partial(_event, option)
        for char in option.chars:
            registry.add_binding(char)(handler)
        if option.fallback:
            registry.add_binding(Keys.ControlC)(handler)
            registry.add_binding(Keys.Escape)(handler)
        if option.default:
            registry.add_binding(Keys.Enter)(handler)

    sys.stdout.flush()

    return run_application(create_prompt_application(
        get_prompt_tokens=_get_tokens,
        style=styling,
        key_bindings_registry=registry,
    ))


class SelectOption():
    def __init__(self, caption, value, *,
                 chars='', default=False, fallback=False, output=None):
        self.caption = caption
        self.value = value
        self.chars = chars
        self.default = default
        self.fallback = fallback
        self.output = output or chars[0]


select.Option = SelectOption


class PromptToolkitUi():
    def mirror_update(self, mirror, action):
        print()
        print(f'\033[01;32m{mirror.name}\033[0m')
        print('='*len(mirror.name))
        action()

    def prepare_switch(self, publish, component):
        self.current_switch = (publish, component)
        print()
        print(f'\033[01m{publish.alias}/{component}\033[0m')
        print('-'*(len(publish.alias) + len(component) + 1))

    def skip_switch(self):
        publish, component = self.current_switch
        print(f'Skipping publication for {publish.target}/{publish.distribution} {component} - no change')

    def include_snapshot(self, snapshot, info):
        print(info)
        return select(
            f'Do you want to include this snapshot',
            select.Option('yes', snapshot, chars='Yy', default=True),
            select.Option('no', False, chars='Nn', fallback=True),
        )

    def update_snapshot(self, current, proposed, *, diff, source):
        print(diff)
        return select(
            f'Include update version in {source.name}',
            select.Option('yes', proposed, chars='YyUuJjZz'),
            select.Option('no', current, chars='Nn', default=True),
            select.Option('abort', None, chars='Aa', fallback=True),
        )

    def remove_snapshot(self, current, info):
        print(info)
        return select(
            f'Do you want to remove this snapshot',
            select.Option('no', info, chars='Nn', default=True, fallback=True),
            select.Option('yes', False, chars='Yy'),
        )

    def switch(self, diff, *, target, distribution, component):
        print(diff)
        return select(
            f'Do you want to publish this change to '
            f'{target}/{distribution} {component}',
            select.Option('no', False, chars='Nn',
                          default=True, fallback=True),
            select.Option('yes', True, chars='Yy')
        )


class CronUI():
    def mirror_update(self, mirror, action):
        action(quiet=True)

    def include_snapshot(self, snapshot, info):
        return snapshot

    def update_snapshot(self, current, proposed, *, diff, source):
        return proposed

    def remove_snapshot(self, current, info):
        return False

    def prepare_switch(self, publish, component):
        self.current_switch = (publish, component)

    def skip_switch(self):
        pass

    def switch(self, diff, *, target, distribution, component):
        publish, component = self.current_switch
        print()
        print(f'{publish.alias}/{component}')
        print('-'*(len(publish.alias) + len(component) + 1))
        print(diff)
        return False
