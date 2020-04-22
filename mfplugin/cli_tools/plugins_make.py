#!/usr/bin/env python3

import argparse
from mfplugin.manager import PluginsManager
from mfutil.cli import echo_ok, echo_running, echo_nok, echo_bold

DESCRIPTION = "make a plugin from the current directory"


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--plugin-path", default=".",
                            help="plugin directory path")
    arg_parser.add_argument("--debug", action="store_true",
                            help="add some debug informations in "
                            "case of problems")
    arg_parser.add_argument("--show-plugin-path", action="store_true",
                            default=False,
                            help="show the generated plugin path")
    args = arg_parser.parse_args()
    echo_running("- Building plugin...")
    manager = PluginsManager()
    try:
        plugin = manager.make_plugin(args.plugin_path)
        path = plugin.build()
    except Exception as e:
        echo_nok()
        print(e)
        if args.debug:
            print("details of the problem:")
            raise(e)
        else:
            print("note: use --debug option for more details")
    else:
        echo_ok()
        if args.show_plugin_path:
            echo_bold("plugin file is ready at %s" % path)


if __name__ == '__main__':
    main()
