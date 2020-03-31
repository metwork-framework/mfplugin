import re
import os

MFMODULE = os.environ.get('MFMODULE', 'MFEXT')
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'mfext')
PLUGIN_NAME_REGEXP = "^[A-Za-z0-9_-]+$"


def validate_plugin_name(plugin_name):
    """Validate a plugin name.

    Args:
        plugin_name (string): the plugin name to validate.

    Returns:
        (boolean, message): (True, None) if the plugin name is ok,
            (False, "error message") if the plugin name is not ok.
    """
    if plugin_name.startswith("plugin_"):
        return (False, "A plugin name can't start with 'plugin_'")
    if plugin_name.startswith("__"):
        return (False, "A plugin name can't start with '__'")
    if plugin_name == "base":
        return (False, "A plugin name can't be 'base'")
    if not re.match(PLUGIN_NAME_REGEXP, plugin_name):
        return (False, "A plugin name must follow %s" % PLUGIN_NAME_REGEXP)
    return (True, None)


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
        raise Exception("bad layerapi2_label: %s => is it really a plugin ?" %
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
        raise Exception("can't read %s file" % llf_path)
    return layerapi2_label_to_plugin_name(c)


def inside_a_plugin_env():
    """Return True if we are inside a plugin_env.

    Returns:
        (boolean): True if we are inside a plugin_env, False else
    """
    return ("%s_CURRENT_PLUGIN_NAME" % MFMODULE) in os.environ


def get_plugin_env_prefix(plugin_name):
    return "%s_PLUGIN_%s" % (MFMODULE, plugin_name.upper())


def get_plugin_env(plugin_name, section, key):
    return "%s_%s_%s" % (get_plugin_env_prefix(plugin_name),
                         section.upper(), key.upper())


def validate_configparser(v, cpobj, schema):
    document = {}
    for section in cpobj.sections():
        document[section] = {}
        for key in cpobj.options(section):
            document[section][key] = cpobj.get(section, key)
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
