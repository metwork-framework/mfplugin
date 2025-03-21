#!/usr/bin/env python3

import os
import argparse
import sys
import json
from mfplugin.manager import PluginsManager
from terminaltables3 import DoubleTable
from mflog import get_logger

DESCRIPTION = "get the installed plugins list"
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'generic')
LOGGER = get_logger("mfplugin/plugins_list")


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("--raw", action="store_true", help="raw mode")
    arg_parser.add_argument("--json", action="store_true", help="json mode "
                            "(not compatible with raw mode)")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    args = arg_parser.parse_args()
    if args.json and args.raw:
        print("ERROR: json and raw options are mutually exclusives")
        sys.exit(1)
    manager = PluginsManager(plugins_base_dir=args.plugins_base_dir)
    plugins = manager.plugins.values()
    json_output = []
    table_data = []
    table_data.append(["Name", "Version", "Release", "Home"])
    for plugin in plugins:
        try:
            release = plugin.release
            version = plugin.version
        except Exception as e:
            LOGGER.warning("Bad plugin: (%s, %s) with exception: %s " %
                           (plugin.name, plugin.home, e))
            release = "error"
            version = "error"
        if args.raw:
            print("%s~~~%s~~~%s~~~%s" % (plugin.name, version, release,
                                         plugin.home))
        elif args.json:
            json_output.append({
                "name": plugin.name,
                "release": release,
                "version": version,
                "home": plugin.home
            })
        else:
            table_data.append([plugin.name, version, release, plugin.home])
    if not args.raw and not args.json:
        t = DoubleTable(title="Installed plugins (%i)" % len(plugins),
                        table_data=table_data)
        print(t.table)
    elif args.json:
        print(json.dumps(json_output, indent=4))


if __name__ == '__main__':
    main()
