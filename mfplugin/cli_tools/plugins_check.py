#!/usr/bin/env python3

import argparse
import sys
from mfplugin.manager import PluginsManager
from mfplugin.utils import get_nice_dump
from mfutil.cli import echo_ok, echo_running, echo_nok, echo_bold

DESCRIPTION = "make a plugin from the current directory"


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("PLUGIN_PATH", default=".",
                            help="plugin directory path to check")
    arg_parser.add_argument("--debug", action="store_true",
                            help="add some debug informations in "
                            "case of problems")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    args = arg_parser.parse_args()
    echo_running("- Checking plugin...")
    manager = PluginsManager(args.plugins_base_dir)
    try:
        plugin = manager.make_plugin(args.PLUGIN_PATH)
        plugin.load_full()
        if args.debug:
            print(get_nice_dump(plugin._get_debug()))
    except Exception as e:
        echo_nok()
        echo_bold(str(e))
        if args.debug:
            print("details of the problem:")
            raise(e)
        else:
            print("(note: use 'plugins.check --debug /plugin/path' "
                  "for more details)")
            sys.exit(1)
    echo_ok()


if __name__ == '__main__':
    main()
