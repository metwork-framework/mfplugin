#!/usr/bin/env python3

import os
import argparse
import sys
import io
import contextlib
import pathlib
from mfplugin.utils import inside_a_plugin_env
from mfplugin.manager import PluginsManager
from mfplugin.utils import NotInstalledPlugin
from mfutil.cli import echo_running, echo_nok, echo_ok

DESCRIPTION = "uninstall a plugin"
MFMODULE_RUNTIME_HOME = os.environ.get('MFMODULE_RUNTIME_HOME', '/tmp')
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')


def main():
    arg_parser = argparse.ArgumentParser(description=DESCRIPTION)
    arg_parser.add_argument("name_or_path", type=str,
                            help="plugin name (or path)")
    arg_parser.add_argument(
        "--clean", action="store_true",
        help="if set, we drop any configuration override "
        "under ${MODULE_HOME}/config/plugins/ for this "
        "plugin (warning: delete nothing under /etc/metwork.config.d/"
        f"{MFMODULE_LOWERCASE}/plugins/)")
    arg_parser.add_argument("--plugins-base-dir", type=str, default=None,
                            help="can be use to set an alternate "
                            "plugins-base-dir, if not set the value of "
                            "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                            "hardcoded standard value).")
    args = arg_parser.parse_args()
    name = pathlib.PurePath(args.name_or_path).name
    if inside_a_plugin_env():
        print("ERROR: Don't use plugins.install/uninstall inside a plugin_env")
        sys.exit(1)
    manager = PluginsManager(plugins_base_dir=args.plugins_base_dir)
    echo_running("- Uninstalling plugin %s..." % name)
    try:
        out = io.StringIO()
        err = io.StringIO()
        with contextlib.redirect_stdout(out):
            with contextlib.redirect_stderr(err):
                manager.uninstall_plugin(name)
    except NotInstalledPlugin:
        echo_nok("not installed")
        sys.exit(1)
    except Exception as e:
        echo_nok()
        print(err.getvalue(), file=sys.stderr)
        print(out.getvalue())
        print(e)
        sys.exit(2)
    finally:
        try:
            os.unlink(f"{MFMODULE_RUNTIME_HOME}/config/plugins/{name}.ini")
        except Exception:
            pass
    echo_ok()


if __name__ == '__main__':
    main()
