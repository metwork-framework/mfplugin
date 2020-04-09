#!/usr/bin/env python3

import os
import sys
import argparse
from mfplugin.manager import PluginsManager
from mfplugin.utils import plugin_name_to_layerapi2_label, NotInstalledPlugin
import shlex

DESCRIPTION = "execute a command in a plugin environment"

MFMODULE = os.environ["MFMODULE"]
MFMODULE_HOME = os.environ["MFMODULE_HOME"]
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
MFMODULE_LOWERCASE = os.environ["MFMODULE_LOWERCASE"]


def main():
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("--cwd",
                        action="store_true",
                        help="change working directory to plugin home")
    parser.add_argument("--empty",
                        action="store_true",
                        help="unload all layers before")
    parser.add_argument("--bash-cmds", action="store_true",
                        help="if set don't execute command but output bash "
                        "cmds to be execute in a fresh empty shell"
                        "(--empty and COMMAND_AND_ARGS ignored)")
    parser.add_argument("--plugins-base-dir", type=str, default=None,
                        help="can be use to set an alternate "
                        "plugins-base-dir, if not set the value of "
                        "MFMODULE_PLUGINS_BASE_DIR env var is used (or a "
                        "hardcoded standard value).")
    parser.add_argument("PLUGIN_NAME", type=str,
                        help="plugin name")
    parser.add_argument("COMMAND_AND_ARGS", nargs='+',
                        help="command (and args )to execute")
    args = parser.parse_args()
    plugin = args.PLUGIN_NAME
    layer_name = plugin_name_to_layerapi2_label(plugin)

    if args.plugins_base_dir is not None:
        plugins_base_dir = args.plugins_base_dir
    else:
        # we check that the plugins base dir is included in
        # LAYERAPI2_LAYERS_PATH
        # (useful for custom plugins base dir during hotswapping for example)
        plugins_base_dir = os.environ.get('MFMODULE_PLUGINS_BASE_DIR', None)
        if plugins_base_dir is not None:
            if plugins_base_dir not in \
                    os.environ.get('LAYERAPI2_LAYERS_PATH', '').split(':'):
                os.environ['LAYERAPI2_LAYERS_PATH'] = \
                    plugins_base_dir + ':' + \
                    os.environ['LAYERAPI2_LAYERS_PATH']

    manager = PluginsManager(plugins_base_dir)
    try:
        p = manager.get_plugin(plugin)
    except NotInstalledPlugin:
        print("ERROR: the plugin %s does not seem to be "
              "installed/available" % plugin, file=sys.stderr)
        sys.exit(1)

    if args.bash_cmds:
        print("source /etc/profile")
        print("if test -f %s/.bash_profile; then source %s/.bash_profile; fi" %
              (MFMODULE_RUNTIME_HOME, MFMODULE_RUNTIME_HOME))
        print("source %s/share/interactive_profile" % MFMODULE_HOME)
        plugin_env = p.get_plugin_env_dict()
        for k, v in plugin_env.items():
            print("export %s=%s" % (k, shlex.quote(v)))
        print("layer_load %s >/dev/null" % layer_name)
        if args.cwd:
            print("cd %s" % p.home)
        sys.exit(0)

    with p.plugin_env_context():
        lw_args = ["--empty",
                   "--layers=%s" % layer_name]
        if args.cwd:
            lw_args.append("--cwd")
        if args.empty:
            lw_args.append("--empty")
        lw_args.append("--")
        for cmd_arg in args.COMMAND_AND_ARGS:
            lw_args.append(cmd_arg)
        os.execvp("layer_wrapper", lw_args)


if __name__ == "__main__":
    main()
