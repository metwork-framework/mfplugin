#!/usr/bin/env python3

import os
import sys
import argparse
from mfplugin.compat import PluginsManager
from mfplugin.utils import NotInstalledPlugin
import shlex

DESCRIPTION = "execute a command in a plugin environment"

MFMODULE = os.environ.get("MFMODULE", "GENERIC")
MFMODULE_HOME = os.environ.get("MFMODULE_HOME", "/tmp")
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
MFMODULE_LOWERCASE = os.environ.get("MFMODULE_LOWERCASE", "generic")
MFMODULE_PLUGINS_BASE_DIR = os.environ.get('MFMODULE_PLUGINS_BASE_DIR', None)
LAYERAPI2_LAYERS_PATH = os.environ.get('LAYERAPI2_LAYERS_PATH', '')


def _prepend(original, new):
    return ":".join([new] + [x for x in original.split(':') if x != new])


def get_new_layerapi2_layers_path(p, add_plugin_home=False):
    # prepend p.home in LAYERAPI2_LAYERS_PATH
    # can be usefull if the plugin is not already installed
    res = LAYERAPI2_LAYERS_PATH
    if MFMODULE_PLUGINS_BASE_DIR:
        # we are probably during a hotswap
        # Let's prepend this repository in LAYERAPI2_LAYERS_PATH
        res = _prepend(res, MFMODULE_PLUGINS_BASE_DIR)
    if add_plugin_home:
        res = _prepend(res, p.home)
    return res


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
    parser.add_argument("PLUGIN_NAME_OR_PLUGIN_HOME", type=str,
                        help="plugin name or plugin home (if starting by /)")
    parser.add_argument("COMMAND_AND_ARGS", nargs='+',
                        help="command (and args )to execute")
    args = parser.parse_args()

    if args.plugins_base_dir is not None:
        plugins_base_dir = args.plugins_base_dir
    else:
        plugins_base_dir = None

    manager = PluginsManager(plugins_base_dir)
    if '/' in args.PLUGIN_NAME_OR_PLUGIN_HOME:
        p = manager.make_plugin(args.PLUGIN_NAME_OR_PLUGIN_HOME)
        mode = "file"
    else:
        mode = "name"
        try:
            p = manager.get_plugin(args.PLUGIN_NAME_OR_PLUGIN_HOME)
        except NotInstalledPlugin:
            print("ERROR: the plugin %s does not seem to be "
                  "installed/available" % args.PLUGIN_NAME_OR_PLUGIN_HOME,
                  file=sys.stderr)
            sys.exit(1)

    if args.bash_cmds:
        print("source /etc/profile")
        print("if test -f %s/.bash_profile; then source %s/.bash_profile; fi" %
              (MFMODULE_RUNTIME_HOME, MFMODULE_RUNTIME_HOME))
        print("source %s/share/interactive_profile" % MFMODULE_HOME)
        plugin_env = p.get_plugin_env_dict()
        for k, v in plugin_env.items():
            print("export %s=%s" % (k, shlex.quote(v)))
        new_layerapi2_layers_path = get_new_layerapi2_layers_path(
            p, add_plugin_home=(mode == "file"))
        if new_layerapi2_layers_path != LAYERAPI2_LAYERS_PATH:
            print("export LAYERAPI2_LAYERS_PATH=%s" %
                  new_layerapi2_layers_path)
        print("layer_load %s >/dev/null" % p.layerapi2_layer_name)
        if args.cwd:
            print("cd %s" % p.home)
        sys.exit(0)

    with p.plugin_env_context():
        new_layerapi2_layers_path = get_new_layerapi2_layers_path(
            p, add_plugin_home=(mode == "file"))
        if new_layerapi2_layers_path != LAYERAPI2_LAYERS_PATH:
            os.environ["LAYERAPI2_LAYERS_PATH"] = new_layerapi2_layers_path
        lw_args = ["--empty",
                   "--layers=%s" % p.layerapi2_layer_name]
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
