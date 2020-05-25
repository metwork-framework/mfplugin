#!/usr/bin/env python3

import os
import argparse
import sys
from mfplugin.manager import PluginsManager
from mfplugin.utils import AlreadyInstalledPlugin
from mfutil.cli import echo_ok, echo_running, echo_nok, echo_bold, echo_warning

DESCRIPTION = "develop a plugin from a directory"
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--plugin-path", default=".",
                            help="plugin directory path")
    arg_parser.add_argument("--ignore-already-installed", action="store_true",
                            help="ignore already installed plugin "
                            "(in dev mode)")
    arg_parser.add_argument("name",
                            help="plugin name")
    args = arg_parser.parse_args()
    manager = PluginsManager()
    echo_running("- Devlinking plugin %s..." % args.name)
    try:
        manager.develop_plugin(args.plugin_path)
    except AlreadyInstalledPlugin:
        if args.ignore_already_installed:
            p = manager.make_plugin(args.plugin_path)
            if p.is_installed and p.is_dev_linked:
                echo_warning("(already installed)")
                sys.exit(0)
        echo_nok()
        echo_bold("ERROR: the plugin is already installed")
        sys.exit(3)
    except Exception as e:
        echo_nok()
        echo_bold(str(e))
        sys.exit(2)
    echo_ok()
    p = manager.get_plugin(args.name)
    p.print_dangerous_state()


if __name__ == '__main__':
    main()
