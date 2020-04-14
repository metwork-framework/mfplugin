#!/usr/bin/env python3

import os
import argparse
import sys
from mfplugin.utils import inside_a_plugin_env
from mfplugin.manager import PluginsManager
from mfplugin.file import PluginFile
from mfplugin.utils import BadPluginFile, AlreadyInstalledPlugin, \
    validate_plugin_name, BadPluginName
from mfutil.cli import echo_running, echo_nok, echo_ok, echo_bold

DESCRIPTION = "install a plugin file"
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("plugin_filepath", type=str,
                            help="plugin filepath")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    arg_parser.add_argument("--new-name", type=str, default=None,
                            help="install the plugin but with a new name "
                            "given by this parameter")
    args = arg_parser.parse_args()
    if inside_a_plugin_env():
        print("ERROR: Don't use plugins.install/uninstall inside a plugin_env")
        sys.exit(1)
    if args.new_name is not None:
        try:
            validate_plugin_name(args.new_name)
        except BadPluginName as e:
            echo_bold("ERROR: bad plugin name for --new-name option")
            echo_bold(str(e))
            sys.exit(3)
    manager = PluginsManager(plugins_base_dir=args.plugins_base_dir)
    if not manager.initialized:
        echo_bold("ERROR: the module is not initialized")
        echo_bold("       => start it once before installing your plugin")
        print()
        print("hint: you can use %s.start to do that" % MFMODULE_LOWERCASE)
        print()
        sys.exit(3)
    echo_running("- Checking plugin file...")
    try:
        pf = PluginFile(args.plugin_filepath)
        pf.load()
    except BadPluginFile:
        echo_nok()
        sys.exit(1)
    echo_ok()
    name = pf.name
    if args.new_name is not None:
        echo_running("- Installing plugin %s as %s..." % (name, args.new_name))
    else:
        echo_running("- Installing plugin %s..." % name)
    try:
        manager.install_plugin(args.plugin_filepath, new_name=args.new_name)
    except AlreadyInstalledPlugin:
        echo_nok("already installed")
        sys.exit(1)
    except Exception as e:
        echo_nok()
        echo_bold(str(e))
        sys.exit(2)
    echo_ok()
    p = manager.get_plugin(args.new_name if args.new_name is not None
                           else name)
    p.print_dangerous_state()


if __name__ == '__main__':
    main()
