import os
import fnmatch
from opinionated_configparser import OpinionatedConfigParser
from cerberus import Validator
from mflog import get_logger
from mfplugin.utils import validate_configparser, \
    cerberus_errors_to_human_string
from mfplugin.app import APP_SCHEMA, App
from mfplugin.extra_daemon import EXTRA_DAEMON_SCHEMA, ExtraDaemon
from mfplugin.utils import BadPlugin, resolve, get_current_envs, \
    PluginEnvContextManager, NON_REQUIRED_BOOLEAN_DEFAULT_TRUE, \
    get_app_class, get_extra_daemon_class


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
            "_add_plugin_dir_to_python_path": {
                **NON_REQUIRED_BOOLEAN_DEFAULT_TRUE
            }
        },
    },
    "app_*": {
        "required": False,
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            **APP_SCHEMA
        },
    },
    "extra_daemon_*": {
        "required": False,
        "type": "dict",
        "allow_unknown": True,
        "schema": {
            **EXTRA_DAEMON_SCHEMA
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

    def __init__(self, plugin_name, plugin_home, config_filepath=None,
                 extra_daemon_class=None,
                 app_class=None):
        self.plugin_name = plugin_name
        self.plugin_home = plugin_home
        self.app_class = get_app_class(app_class, App)
        self.extra_daemon_class = get_extra_daemon_class(extra_daemon_class,
                                                         ExtraDaemon)
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
        self._commands = None
        self._doc = None
        self.__loaded = False

    def get_schema(self):
        return SCHEMA

    def get_configuration_env_dict(self, ignore_keys_starting_with=None):
        self.load()
        env_var_dict = {}
        for section in self._doc.keys():
            for option in self._doc[section].keys():
                if ignore_keys_starting_with and \
                        option.strip().startswith(ignore_keys_starting_with):
                    continue
                val = self._parser.get(section, option)
                name = "%s_PLUGIN_%s_%s_%s" % \
                    (MFMODULE, self.plugin_name.upper(),
                     section.upper().replace('-', '_'),
                     option.upper().replace('-', '_'))
                env_var_dict[name] = val
        return env_var_dict

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

    def get_final_document(self, validated_document):
        return validated_document

    def __get_final_document(self, validated_document):
        vdocument = {}
        for section in validated_document.keys():
            for option in validated_document[section].keys():
                val = validated_document[section][option]
                if option.endswith("_hostname") or option == "hostname":
                    if "%s_ip" % option not in validated_document[section]:
                        new_val = resolve(val)
                        if new_val is None:
                            new_val = "dns_error"
                        vdocument[section]["%s_ip" % option] = new_val
                elif option.endswith("_hostnames") or option == "hostnames":
                    if "%s_ips" % option not in validated_document[section]:
                        hostname_list = val.split(";")
                        new_vals = []
                        for hostname in hostname_list:
                            new_val = resolve(hostname)
                            if new_val is None:
                                new_val = "dns_error"
                            new_vals.append(new_val)
                        vdocument[section]["%s_ips" % option] = \
                            ";".join(new_vals)
                if section not in vdocument:
                    vdocument[section] = {}
                vdocument[section][option] = val
        return self.get_final_document(vdocument)

    def __load(self):
        if self.__loaded:
            return False
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
        self._doc = self.__get_final_document(v.document)
        self._apps = []
        self._extra_daemons = []
        # FIXME: step mfdata ?
        for section in [x for x in self._doc.keys() if x.startswith("app_")]:
            c = self.app_class
            command = c(self.plugin_name,
                        section.replace('app_', '', 1),
                        self._doc[section])
            self.add_app(command)
        for section in [x for x in self._doc.keys()
                        if x.startswith("extra_daemon_")]:
            c = self.extra_daemon_class
            command = c(self.plugin_name,
                        section.replace('extra_daemon_', '', 1),
                        self._doc[section])
            self.add_extra_daemon(command)
        return True

    def load(self):
        with PluginEnvContextManager(get_current_envs(self.plugin_name,
                                                      self.plugin_home)):
            return self.__load()

    def add_app(self, app):
        self.load()
        self._apps.append(app)

    def add_extra_daemon(self, extra_daemon):
        self.load()
        self._extra_daemons.append(extra_daemon)

    def load_full(self):
        self.load()

    @property
    def apps(self):
        self.load()
        return self._apps

    @property
    def extra_daemons(self):
        self.load()
        return self._extra_daemons

    @property
    def version(self):
        self.load()
        return self._doc['general']['_version']

    @property
    def summary(self):
        self.load()
        return self._doc['general']['_summary']

    @property
    def license(self):
        self.load()
        return self._doc['general']['_license']

    @property
    def maintainer(self):
        self.load()
        return self._doc['general']['_maintainer']

    @property
    def packager(self):
        return self.maintainer

    @property
    def vendor(self):
        self.load()
        return self._doc['general']['_vendor']

    @property
    def url(self):
        self.load()
        return self._doc['general']['_url']
