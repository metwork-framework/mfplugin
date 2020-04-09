#!/usr/bin/env python3

import os
import argparse
import sys
from mfplugin.utils import inside_a_plugin_env
from mfplugin.manager import PluginsManager
from mfplugin.file import PluginFile
from mfplugin.utils import BadPluginFile, AlreadyInstalledPlugin
from mfutil.cli import echo_running, echo_nok, echo_ok, echo_bold

DESCRIPTION = "install a plugin file"
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("plugin_filepath", type=str,
                            help="plugin filepath")
    arg_parser.add_argument("--force", help="ignore some errors",
                            action="store_true")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    args = arg_parser.parse_args()
    if inside_a_plugin_env():
        print("ERROR: Don't use plugins.install/uninstall inside a plugin_env")
        sys.exit(1)
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
        pf = PluginFile(args.plugin_filepath,
                        plugins_base_dir=manager.plugins_base_dir)
        pf.load()
    except BadPluginFile:
        echo_nok()
        sys.exit(1)
    echo_ok()
    name = pf.name
    echo_running("- Installing plugin %s..." % name)
    try:
        manager.install_plugin(args.plugin_filepath)
    except AlreadyInstalledPlugin:
        echo_nok("already installed")
        sys.exit(1)
    except Exception as e:
        echo_nok()
        echo_bold(str(e))
        sys.exit(2)
    echo_ok()
    p = manager.get_plugin(name)
    p.print_dangerous_state()


if __name__ == '__main__':
    main()
