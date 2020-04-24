#!/usr/bin/env python3

import os
import io
import contextlib
import argparse
import sys
from mfplugin.utils import inside_a_plugin_env
from mfplugin.manager import PluginsManager
from mfplugin.utils import NotInstalledPlugin
from mfutil.cli import echo_running, echo_nok, echo_ok, echo_bold

DESCRIPTION = "repacke and installed plugin"
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("name", type=str,
                            help="plugin name")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    arg_parser.add_argument("--debug", action="store_true",
                            help="add some debug informations in "
                            "case of problems")
    args = arg_parser.parse_args()
    name = args.name
    if inside_a_plugin_env():
        print("ERROR: Don't use plugins.install/uninstall inside a plugin_env")
        sys.exit(1)
    manager = PluginsManager(plugins_base_dir=args.plugins_base_dir)
    echo_running("- Repackaging plugin %s..." % name)
    try:
        f = io.StringIO()
        with contextlib.redirect_stderr(f):
            path = manager.repackage_plugin(name)
    except NotInstalledPlugin:
        echo_nok()
        echo_bold(" => not installed plugin")
        sys.exit(1)
    except Exception as e:
        echo_nok()
        stderr = f.getvalue()
        if stderr != '':
            print(stderr)
        print(e)
        if args.debug:
            print("details of the problem:")
            raise(e)
        else:
            print("note: use --debug option for more details")
    else:
        echo_ok()
        stderr = f.getvalue()
        if stderr != '':
            print(stderr)
        echo_bold("plugin file is ready at %s" % path)


if __name__ == '__main__':
    main()
