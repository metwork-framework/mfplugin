import os
import fnmatch
from opinionated_configparser import OpinionatedConfigParser
from cerberus import Validator
from mflog import get_logger
from mfplugin.utils import validate_configparser, \
    cerberus_errors_to_human_string
from mfplugin.command import COMMAND_SCHEMA, Command
from mfplugin.utils import BadPlugin, resolve

MFMODULE = os.environ.get("MFMODULE", "GENERIC")
MFMODULE_LOWERCASE = os.environ.get("MFMODULE_LOWERCASE", "generic")
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")

SCHEMA = {
    "general": {
        "required": True,
        "type": "dict",
        "schema": {
            "_version": {"required": True, "type": "string",
                         "regex": r"^[a-z0-9-_]+\.[a-z0-9-_]+\.[a-z0-9-_]+$"},
            "_summary": {"required": True, "type": "string", "minlength": 1},
            "_license": {"required": True, "type": "string", "minlength": 1},
            "_url": {"required": True, "type": "string", "minlength": 1},
            "_maintainer": {"required": True, "type": "string",
                            "minlength": 1},
            "_vendor": {"required": True, "type": "string", "minlength": 1},
        },
    },
    "app_*": {
        "required": False,
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            **COMMAND_SCHEMA
        },
    },
    "extra_daemon_*": {
        "required": False,
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            **COMMAND_SCHEMA
        },
    },
    "custom": {
        "required": False,
        "type": "dict",
        "allow_unknown": True,
        "schema": {}
    },
}
LOGGER = get_logger("configuration.py")


class Configuration(object):

    __loaded = None
    plugin_name = None
    plugin_home = None
    _parser = None
    _version = None
    _commands = None
    _config_filepath = None
    _summary = None
    _license = None
    _packager = None
    _vendor = None
    _url = None
    command_class = None
    paths = None

    def __init__(self, plugin_name, plugin_home, config_filepath=None,
                 command_class=Command):
        self.plugin_name = plugin_name
        self.plugin_home = plugin_home
        self.command_class = command_class
        if config_filepath is None:
            self._config_filepath = os.path.join(plugin_home, "config.ini")
        else:
            self._config_filepath = config_filepath
        if not os.path.isfile(self._config_filepath):
            raise BadPlugin("configuration file: %s is missing" %
                            self._config_filepath)
        self.paths = [
            self._config_filepath,
            "%s/config/plugins/%s.ini" % (MFMODULE_RUNTIME_HOME,
                                          self.plugin_name),
            "/etc/metwork.config.d/%s/external_plugins/%s.ini" %
            (MFMODULE_LOWERCASE, self.plugin_name),
            "/etc/metwork.config.d/%s/plugins/%s.ini" %
            (MFMODULE_LOWERCASE, self.plugin_name)
        ]
        self.__loaded = False

    def get_schema(self):
        return SCHEMA

    def get_configuration_env_dict(self, ignore_keys_starting_with=None,
                                   add_resolved=True):
        def add_env_var(env_var_dict, section, option, val):
            name = "%s_PLUGIN_%s_%s_%s" % \
                (MFMODULE, self.plugin_name.upper(),
                 section.upper().replace('-', '_'),
                 option.upper().replace('-', '_'))
            env_var_dict[name] = val
        self.load()
        res = {}
        for section in self._parser.sections():
            for option in self._parser.options(section):
                if ignore_keys_starting_with and \
                        option.strip().startswith(ignore_keys_starting_with):
                    continue
                val = self._parser.get(section, option)
                if add_resolved:
                    if option.lower().endswith("_hostname") or \
                            option.lower() == "hostname":
                        if not self._parser.has_option(section,
                                                       "%s_ip" % option):
                            new_val = resolve(val)
                            if new_val is None:
                                new_val = "dns_error"
                            add_env_var(res, section, option + "_IP", new_val)
                    elif option.lower().endswith("_hostnames") or \
                            option.lower() == "hostnames":
                        if not self._parser.has_option(section,
                                                       "%s_ips" % option):
                            hostname_list = val.split(";")
                            new_vals = []
                            for hostname in hostname_list:
                                new_val = resolve(hostname)
                                if new_val is None:
                                    new_val = "dns_error"
                                new_vals.append(new_val)
                            add_env_var(res, section, option + "_IP",
                                        ";".join(new_vals))
                add_env_var(res, section, option, val)
        return res

    def __get_schema(self):
        schema = self.get_schema()
        to_delete = [x for x in schema.keys() if "*" in x or "?" in x]
        for key in to_delete:
            orig = schema[key]
            del schema[key]
            for section in self._parser.sections():
                if fnmatch.fnmatch(section, key):
                    schema[section] = orig.copy()
        return schema

    def load(self):
        if self.__loaded:
            return
        self.__loaded = True
        self._parser = OpinionatedConfigParser()
        self._parser.read(self.paths)
        v = Validator()
        v.allow_unknown = True
        v.require_all = True
        status = validate_configparser(v, self._parser, self.__get_schema())
        if status is False:
            errors = cerberus_errors_to_human_string(v.errors)
            LOGGER.warning(
                "bad plugin configuration file for plugin: %s => "
                "please fix %s/config.ini or corresponding overiddes\n\n%s"
                % (self.plugin_name, self.plugin_home, errors)
            )
            raise BadPlugin("invalid configuration file: %s" %
                            self._config_filepath)
        self._version = self._parser.get("general", "_version")
        self._summary = self._parser.get("general", "_summary")
        self._license = self._parser.get("general", "_license")
        self._maintainer = self._parser.get("general", "_maintainer")
        self._packager = self._maintainer
        self._vendor = self._parser.get("general", "_vendor")
        self._url = self._parser.get("general", "_url")
        self._commands = []
        for prefix in ("app_", "extra_daemon_"):
            for section in [x for x in self._parser.sections()
                            if x.startswith(prefix)]:
                c = self.command_class
                command = c(self.plugin_name, self._parser, section)
                self._commands.append(command)

    def load_full(self):
        self.load()
        [x.load() for x in self.commands]

    @property
    def commands(self):
        self.load()
        return self._commands

    @property
    def version(self):
        self.load()
        return self._version

    @property
    def summary(self):
        self.load()
        return self._summary

    @property
    def license(self):
        self.load()
        return self._license

    @property
    def maintainer(self):
        self.load()
        return self._maintainer

    @property
    def packager(self):
        self.load()
        return self._packager

    @property
    def vendor(self):
        self.load()
        return self._vendor

    @property
    def url(self):
        self.load()
        return self._url
