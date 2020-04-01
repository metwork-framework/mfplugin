import re
import os
from mfutil import BashWrapperException

MFMODULE = os.environ.get('MFMODULE', 'GENERIC')
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'generic')
PLUGIN_NAME_REGEXP = "^[A-Za-z0-9_-]+$"


def validate_plugin_name(plugin_name):
    """Validate a plugin name.

    Args:
        plugin_name (string): the plugin name to validate.

    Raises:
        BadPluginName exception if the plugin_name is incorrect.
    """
    if plugin_name.startswith("plugin_"):
        raise BadPluginName("A plugin name can't start with 'plugin_'")
    if plugin_name.startswith("__"):
        raise BadPluginName("A plugin name can't start with '__'")
    if plugin_name == "base":
        raise BadPluginName("A plugin name can't be 'base'")
    if not re.match(PLUGIN_NAME_REGEXP, plugin_name):
        raise BadPluginName("A plugin name must follow %s" %
                            PLUGIN_NAME_REGEXP)


def plugin_name_to_layerapi2_label(plugin_name):
    """Get a layerapi2 label from a plugin name.

    Args:
        plugin_name (string): the plugin name from which we create the label.

     Returns:
         (string): the layerapi2 label.
    """
    return "plugin_%s@%s" % (plugin_name, MFMODULE_LOWERCASE)


def layerapi2_label_to_plugin_name(label):
    """Get the plugin name from the layerapi2 label.

    Args:
        label (string): the label from which we extract the plugin name.

    Returns:
         (string): the plugin name.
    """
    if (not label.startswith("plugin_")) or \
            (not label.endswith("@%s" % MFMODULE_LOWERCASE)):
        raise BadPlugin("bad layerapi2_label: %s => is it really a plugin ?" %
                        label)
    return label[7:].split('@')[0]


def layerapi2_label_file_to_plugin_name(llf_path):
    """Get the plugin name from the layerapi2 label file.

    Args:
        llf_path (string): the layerapi2 label file path from which
            we extract the label.

    Returns:
         (string): the plugin name.
    """
    try:
        with open(llf_path, 'r') as f:
            c = f.read().strip()
    except Exception:
        raise BadPlugin("can't read %s file" % llf_path)
    return layerapi2_label_to_plugin_name(c)


def inside_a_plugin_env():
    """Return True if we are inside a plugin_env.

    Returns:
        (boolean): True if we are inside a plugin_env, False else
    """
    return ("%s_CURRENT_PLUGIN_NAME" % MFMODULE) in os.environ


def get_plugin_env_prefix(plugin_name):
    """Return the env var prefix for the given plugin name.

    Args:
        plugin_name (string): the plugin name.

    Returns:
        The env var prefix for the plugin (string).
    """
    return "%s_PLUGIN_%s" % (MFMODULE, plugin_name.upper())


def get_plugin_env(plugin_name, section, key):
    """Return the env var name given a plugin_name and a configuration key.

    Args:
        plugin_name (string): the plugin name.
        section (string): the name of the configuration section.
        key (string): the name of the configuration key.

    Returns:
        The corresponding env var name.
    """
    return "%s_%s_%s" % (get_plugin_env_prefix(plugin_name),
                         section.upper(), key.upper())


def validate_configparser(v, cpobj, schema):
    document = {}
    for section in cpobj.sections():
        document[section] = {}
        for key in cpobj.options(section):
            document[section][key] = cpobj.get(section, key)
    import json
    print(json.dumps(document, indent=4))
    print(json.dumps(schema, indent=4))
    return v.validate(document, schema)


def cerberus_errors_to_human_string(v_errors):
    errors = ""
    for section in v_errors.keys():
        for error in v_errors[section]:
            if type(error) is str:
                errors = errors + "[section: %s] %s\n" % (section, error)
                continue
            for key in error.keys():
                for error2 in error[key]:
                    errors = errors + \
                        "[section: %s][key: %s] %s\n" % (section, key, error2)
    return errors


class MFPluginException(BashWrapperException):
    """Base mfplugin Exception class."""

    pass


class BadPlugin(MFPluginException):
    """Exception raised when a plugin is badly constructed."""

    pass


class BadPluginConfiguration(BadPlugin):
    """Exception raised when a plugin has a bad configuration."""

    pass


class BadPluginName(BadPlugin):
    """Exception raised when a plugin has an invalid name."""

    pass


class NotInstalledPlugin(MFPluginException):
    """Exception raised when a plugin is not installed."""

    pass


class CantBuildPlugin(MFPluginException):
    """Exception raised when we can't build a plugin."""

    pass


def get_rpm_cmd(plugins_base_dir, command, extra_args="", add_prefix=False):
    base = os.path.join(plugins_base_dir, "base")
    if add_prefix:
        cmd = 'layer_wrapper --layers=rpm@mfext -- rpm %s ' \
            '--dbpath %s --prefix %s %s' % \
            (command, base, plugins_base_dir, extra_args)
    else:
        cmd = 'layer_wrapper --layers=rpm@mfext -- rpm %s ' \
            '--dbpath %s %s' % \
            (command, base, extra_args)
    return cmd


def get_default_plugins_base_dir():
    """Return the default plugins base directory path.

    This value correspond to the content of MFMODULE_PLUGINS_BASE_DIR env var
    or ${RUNTIME_HOME}/var/plugins (if not set).

    Returns:
        (string): the default plugins base directory path.

    """
    if "MFMODULE_PLUGINS_BASE_DIR" in os.environ:
        return os.environ.get("MFMODULE_PLUGINS_BASE_DIR")
    return os.path.join(MFMODULE_RUNTIME_HOME, "var", "plugins")
