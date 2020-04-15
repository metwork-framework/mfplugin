#!/usr/bin/env python3

from __future__ import print_function
import os
import argparse
import sys
import textwrap
from terminaltables import SingleTable
from mfplugin.compat import get_plugin_info

DESCRIPTION = "get some information about a plugin"
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("name_or_filepath", type=str,
                            help="installed plugin name (without version) or "
                            "full plugin filepath")
    arg_parser.add_argument("--just-home", action="store_true",
                            help="if set, just return plugin home")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    args = arg_parser.parse_args()

    infos = get_plugin_info(args.name_or_filepath,
                            plugins_base_dir=args.plugins_base_dir)

    if infos is None:
        sys.exit(1)
    if args.just_home:
        print(infos['home'])
        sys.exit(0)

    table_data = []
    for title, key in [("Name", "name"), ("Version", "version"),
                       ("Release", "release"), ("Summary", "summary"),
                       ("Size", "size"),
                       ("Build Host", "build_host"),
                       ("Build Date", "build_date"),
                       ("License", "license"), ("Maintainer", "packager"),
                       ("Vendor", "vendor"), ("URL", "url")]:
        table_data.append((title, textwrap.fill(infos['metadatas'][key], 60)))
    t = SingleTable(table_data=table_data)
    t.inner_heading_row_border = False
    print(t.table)
    print()
    print("Files:")
    for f in infos['files']:
        print("- %s" % f)


if __name__ == '__main__':
    main()
