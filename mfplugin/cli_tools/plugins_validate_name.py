#!/usr/bin/env python3

import argparse
import sys
from mfplugin.utils import validate_plugin_name, BadPluginName

DESCRIPTION = "validate a plugin name"


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("plugin_name", type=str,
                            help="plugin name candidate")
    args = arg_parser.parse_args()

    try:
        validate_plugin_name(args.plugin_name)
    except BadPluginName as e:
        print("ERROR: %s" % e)
        sys.exit(1)
    print("OK")
    sys.exit(0)


if __name__ == '__main__':
    main()
