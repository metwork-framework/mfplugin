import os
import fnmatch
from opinionated_configparser import OpinionatedConfigParser
from cerberus import Validator
from mflog import get_logger
from mfplugin.utils import validate_configparser, \
    cerberus_errors_to_human_string
from mfplugin.plugin_command import COMMAND_SCHEMA, MFPluginCommand

SCHEMA = {
    "general": {
        "type": "dict",
        "schema": {
            "_version": {"required": True, "type": "string",
                         "regex": "^[a-z0-9-_.]+$"},
            "_summary": {"required": True, "type": "string", "minlength": 1},
            "_license": {"required": True, "type": "string", "minlength": 1},
            "_url": {"required": True, "type": "string", "minlength": 1},
            "_maintainer": {"required": True, "type": "string",
                            "minlength": 1},
            "_vendor": {"required": True, "type": "string", "minlength": 1},
        },
    },
    "app_*": {
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            **COMMAND_SCHEMA
        },
    },
    "extra_daemon_*": {
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            **COMMAND_SCHEMA
        },
    },
    "custom": {"type": "dict", "allow_unknown": True, "schema": {}},
}
LOGGER = get_logger("plugin_configuration.py")


class MFPluginConfiguration(object):

    __loaded = None
    _plugin_name = None
    _plugin_home = None
    _parser = None
    _commands = None
    _config_filepath = None
    plugin_command_class = None

    def __init__(self, plugin_name, plugin_home, config_filepath=None,
                 plugin_command_class=MFPluginCommand):
        self._plugin_name = plugin_name
        self._plugin_home = plugin_home
        if config_filepath is None:
            self._config_filepath = os.path.join(plugin_home, "config.ini")
        else:
            self._config_filepath = config_filepath
        self._MFPluginConfiguration__loaded = False

    def get_schema(self):
        return SCHEMA

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

    def __load(self):
        if self._MFPluginConfiguration__loaded:
            return
        self._MFPluginConfiguration__loaded = True
        self._parser = OpinionatedConfigParser()
        self._parser.read(self._config_filepath)
        v = Validator()
        v.allow_unknown = True
        status = validate_configparser(v, self._parser, self.__get_schema())
        if status is False:
            errors = cerberus_errors_to_human_string(v.errors)
            LOGGER.warning(
                "bad plugin configuration file for plugin: %s => "
                "please fix %s/config.ini\n\n%s"
                % (self._plugin_name, self._plugin_home, errors)
            )
            return
        self._commands = []
        for prefix in ("app_", "extra_daemon_"):
            for section in [x for x in self._parser.sections()
                            if x.startswith(prefix)]:
                command = (self.plugin_command_class)(
                    self._plugin_name, self._parser, section
                )
                self._commands.append(command)

    @property
    def commands(self):
        self.__load()
        return self._commands


p = MFPluginConfiguration("foo", "/home/foo", "toto.ini")
p.commands
# okay decompiling toto.pyc
