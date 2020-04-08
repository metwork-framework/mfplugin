import re
import os
import json
import importlib
from mfutil import BashWrapperException, BashWrapper, get_ipv4_for_hostname, \
    mkdir_p_or_die

__pdoc__ = {
    "PluginEnvContextManager": False
}
MFMODULE = os.environ.get('MFMODULE', 'GENERIC')
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'generic')
PLUGIN_NAME_REGEXP = "^[A-Za-z0-9_-]+$"
UNDER_METWORK_ENV = 'MFCONFIG' in os.environ


class PluginEnvContextManager(object):

    __env_dict = None
    __saved_environ = None

    def __init__(self, env_dict):
        self.__env_dict = env_dict

    def __enter__(self):
        self.__saved_environ = dict(os.environ)
        for key, value in self.__env_dict.items():
            os.environ[key] = value

    def __exit__(self, type, value, traceback):
        os.environ.clear()
        os.environ.update(self.__saved_environ)


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
    if plugin_name == "config":
        raise BadPluginName("A plugin name can't be 'config'")
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
    if not label.startswith("plugin_"):
        raise BadPlugin("bad layerapi2_label: %s => is it really a plugin? "
                        "(it must start with 'plugin_')" % label)
    if not label.endswith("@%s" % MFMODULE_LOWERCASE):
        raise BadPlugin("bad layerapi2_label: %s => is it really a plugin? "
                        "(it must end with '@%s')" %
                        (label, MFMODULE_LOWERCASE))
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


class AlreadyInstalledPlugin(MFPluginException):
    """Exception raised when a plugin is already installed."""

    pass


class CantInstallPlugin(MFPluginException):
    """Exception raised when we can't install a plugin."""

    pass


class CantUninstallPlugin(MFPluginException):
    """Exception raised when we can't uninstall a plugin."""

    pass


class CantBuildPlugin(MFPluginException):
    """Exception raised when we can't build a plugin."""

    pass


class BadPluginFile(MFPluginException):
    """Exception raised when a plugin file is bad."""

    pass


class PluginsBaseNotInitialized(MFPluginException):
    """Exception raised when the plugins base is not initialized."""

    pass


def get_rpm_cmd(plugins_base_dir, command, extra_args="", add_prefix=False):
    base = os.path.join(plugins_base_dir, "base")
    if UNDER_METWORK_ENV:
        before = 'layer_wrapper --layers=rpm@mfext -- '
    else:
        before = ''
    if add_prefix:
        cmd = 'rpm %s --dbpath %s --prefix %s %s' % \
            (command, base, plugins_base_dir, extra_args)
    else:
        cmd = 'rpm %s --dbpath %s %s' % \
            (command, base, extra_args)
    return before + cmd


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


def _touch_conf_monitor_control_file():
    BashWrapper("touch %s/var/conf_monitor" % MFMODULE_RUNTIME_HOME)


def resolve(val):
    if val.lower() == "null" or val.startswith("/"):
        # If it's "null" or linux socket
        return val
    return get_ipv4_for_hostname(val)


def to_bool(strng):
    try:
        return strng.lower() in ('1', 'true', 'yes', 'y', 't')
    except Exception:
        return False


def to_int(strng):
    try:
        return int(strng)
    except Exception:
        return 0


def null_to_empty(value):
    if value == "null":
        return ""
    return value


def get_plugin_lock_path():
    lock_dir = os.path.join(MFMODULE_RUNTIME_HOME, 'tmp')
    lock_path = os.path.join(lock_dir, "plugin_management_lock")
    if not os.path.isdir(lock_dir):
        mkdir_p_or_die(lock_dir)
    return lock_path


def get_current_envs(plugin_name, plugin_home):
    plugin_label = plugin_name_to_layerapi2_label(plugin_name)
    return {
        "%s_CURRENT_PLUGIN_NAME" % MFMODULE: plugin_name,
        "%s_CURRENT_PLUGIN_DIR" % MFMODULE: plugin_home,
        "%s_CURRENT_PLUGIN_LABEL" % MFMODULE: plugin_label
    }


def get_class_from_fqn(class_fqn):
    class_name = class_fqn.split('.')[-1]
    module_path = ".".join(class_fqn.split('.')[0:-1])
    if module_path == "":
        raise Exception("incorrect class_fqn: %s" % class_fqn)
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def __get_class(class_arg, env, default):
    if class_arg is not None:
        return class_arg
    if env in os.environ:
        class_fqn = os.environ[env]
        return get_class_from_fqn(class_fqn)
    return default


def get_configuration_class(configuration_class_arg, default):
    return __get_class(configuration_class_arg, "MFPLUGIN_CONFIGURATION_CLASS",
                       default)


def get_app_class(app_class_arg, default):
    return __get_class(app_class_arg, "MFPLUGIN_APP_CLASS",
                       default)


def get_extra_daemon_class(extra_daemon_class_arg, default):
    return __get_class(extra_daemon_class_arg, "MFPLUGIN_EXTRA_DAEMON_CLASS",
                       default)


def is_jsonable(x):
    try:
        json.dumps(x)
        return True
    except Exception:
        return False


def get_nice_dump(val):
    def default(o):
        return f"<<non-serializable: {type(o).__qualname__}"
    return json.dumps(val, indent=4, default=default)


NON_REQUIRED_BOOLEAN = {
    "required": False,
    "type": "boolean",
    "coerce": (str, to_bool)
}
NON_REQUIRED_BOOLEAN_DEFAULT_FALSE = {
    **NON_REQUIRED_BOOLEAN,
    "default": False
}
NON_REQUIRED_BOOLEAN_DEFAULT_TRUE = {
    **NON_REQUIRED_BOOLEAN,
    "default": True
}
NON_REQUIRED_INTEGER = {
    "required": False,
    "type": "integer",
    "coerce": (str, to_int)
}
NON_REQUIRED_INTEGER_DEFAULT_0 = {
    **NON_REQUIRED_INTEGER,
    "default": 0
}
NON_REQUIRED_STRING = {
    "required": False,
    "type": "string",
    "coerce": (str, null_to_empty),
    "default": ""
}
NON_REQUIRED_STRING_DEFAULT_EMPTY = {
    **NON_REQUIRED_STRING,
    "default": ""
}
