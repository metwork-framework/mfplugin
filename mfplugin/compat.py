import os
import hashlib
from mfplugin.manager import PluginsManager
from mfplugin.file import PluginFile


def get_installed_plugins(plugins_base_dir=None):
    """Get a detailled list of installed plugins.

    This is just a compat helper
    (as the real implementatin is in manager class).

    Args:
       plugins_base_dir (string): (optional) the plugin base directory path.
           If not set, the default plugins base directory path is used.

    Returns:
        (string): dict of installed plugins with following keys: name, version,
            release, home.

    Raises:
        FIXME.

    """
    manager = PluginsManager(plugins_base_dir)
    res = []
    for plugin in manager.plugins.values():
        if not plugin.is_installed:
            continue
        tmp = {
            "name": plugin.name,
            "version": plugin.version,
            "release": plugin.release,
            "home": plugin.home
        }
        res.append(tmp)
    return res


def get_plugin_info(name_or_filepath, mode="auto", plugins_base_dir=None):
    """Get detailed information about a plugin.

    This is just a compat helper
    (as the real implementatin is in manager class).

    Args:
        name_or_filepath (string): name or file path of the plugin.
        mode (string)
            - "name": get information from the plugin name
            (name_or_filepath is the name of the plugin).
            - "file": get information from the plutgin file
            (name_or_filepath is the plugin file path).
            - "auto": guess if the name_or_filepath parameter is the name
            or the file path of the plugin.
        plugins_base_dir (string): (optional) the plugin base directory path.
            If not set, the default plugins base directory path is used.

    Returns:
        (dict): dictionary containing plugin information (or None if the
            plugin is not installed (name mode).

    Raises:
        NotInstalledPlugin: is the plugin is not installed (if it is a "name").

    """
    res = {}
    if mode == "auto":
        mode = "name"
        if '/' in name_or_filepath or '.' in name_or_filepath:
            mode = "file"
        else:
            if os.path.isfile(name_or_filepath):
                mode = "file"
    if mode == "file":
        plugin = PluginFile(name_or_filepath)
    elif mode == "name":
        manager = PluginsManager(plugins_base_dir)
        try:
            plugin = manager.plugins[name_or_filepath]
        except KeyError:
            return None
    else:
        raise Exception("unknown mode: %s" % mode)
    res = {
        "files": plugin.files,
        "home": plugin.home
    }
    res['metadatas'] = {
        "name": plugin.name,
        "release": plugin.release,
        "version": plugin.version,
        "size": plugin.size,
        "build_host": plugin.build_host,
        "build_date": plugin.build_date
    }
    if mode == "file":
        res['metadatas'].update({
            "license": plugin.license,
            "packager": plugin.packager,
            "vendor": plugin.vendor,
            "url": plugin.url,
            "summary": plugin.summary
        })
    else:
        res['metadatas'].update({
            "license": plugin.configuration.license,
            "packager": plugin.configuration.packager,
            "vendor": plugin.configuration.vendor,
            "url": plugin.configuration.url,
            "summary": plugin.configuration.summary
        })
    return res


def get_plugin_hash(name_or_filepath, mode="auto", plugins_base_dir=None):
    """Get a hash about a plugin.

    This is just a compat helper
    (as the real implementatin is in manager class).

    Args:
        name_or_filepath (string): name or file path of the plugin.
        mode (string)
            - "name": get information from the plugin name
            (name_or_filepath is the name of the plugin).
            - "file": get information from the plutgin file
            (name_or_filepath is the plugin file path).
            - "auto": guess if the name_or_filepath parameter is the name
            or the file path of the plugin.
        plugins_base_dir (string): (optional) the plugin base directory path.
            If not set, the default plugins base directory path is used.

    Returns:
        (string): string digest data for the plugin.

    """
    infos = get_plugin_info(name_or_filepath, mode=mode,
                            plugins_base_dir=plugins_base_dir)
    if infos is None:
        return None
    sid = ", ".join([infos['metadatas'].get('build host', 'unknown'),
                     infos['metadatas'].get('build date', 'unknown'),
                     infos['metadatas'].get('size', 'unknown'),
                     infos['metadatas'].get('version', 'unknown'),
                     infos['metadatas'].get('release', 'unknown')])
    return hashlib.md5(sid.encode('utf8')).hexdigest()


def get_layer_home_from_plugin_name(name, plugins_base_dir=None):
    infos = get_plugin_info(name, mode="name",
                            plugins_base_dir=plugins_base_dir)
    if infos is None:
        return None
    return infos['home']
