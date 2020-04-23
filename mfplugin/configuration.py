import os
import copy
import sys
import fnmatch
import inspect
from opinionated_configparser import OpinionatedConfigParser
from cerberus import Validator
from mfplugin.utils import validate_configparser, \
    cerberus_errors_to_human_string
from mfplugin.app import APP_SCHEMA, App
from mfplugin.extra_daemon import EXTRA_DAEMON_SCHEMA, ExtraDaemon
from mfplugin.utils import BadPlugin, resolve, get_current_envs, \
    PluginEnvContextManager, NON_REQUIRED_BOOLEAN_DEFAULT_TRUE, \
    get_app_class, get_extra_daemon_class, get_nice_dump, is_jsonable


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
        "allow_unknown": False,
        "schema": {
            **APP_SCHEMA
        },
    },
    "extra_daemon_*": {
        "required": False,
        "type": "dict",
        "allow_unknown": False,
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
        paths = [
            self._config_filepath,
            "%s/config/plugins/%s.ini" % (MFMODULE_RUNTIME_HOME,
                                          self.plugin_name),
            "/etc/metwork.config.d/%s/plugins/%s.ini" %
            (MFMODULE_LOWERCASE, self.plugin_name)
        ]
        self.paths = [x for x in paths if os.path.isfile(x)]
        self._commands = None
        self._doc = None
        self.__loaded = False

    def get_schema(self):
        return copy.deepcopy(SCHEMA)

    def get_configuration_env_dict(self, ignore_keys_starting_with=None,
                                   limit_to_section=None):
        self.load()
        env_var_dict = {}
        if limit_to_section is None:
            sections = self._doc.keys()
        else:
            if limit_to_section in list(self._doc.keys()):
                sections = [limit_to_section]
            else:
                sections = []
        for section in sections:
            for option in self._doc[section].keys():
                if ignore_keys_starting_with and \
                        option.strip().startswith(ignore_keys_starting_with):
                    continue
                val = self._doc[section][option]
                name = "%s_PLUGIN_%s_%s_%s" % \
                    (MFMODULE, self.plugin_name.upper(),
                     section.upper().replace('-', '_'),
                     option.upper().replace('-', '_'))
                if isinstance(val, bool):
                    env_var_dict[name] = "1" if val else "0"
                else:
                    env_var_dict[name] = "%s" % val
        return env_var_dict

    def __get_schema(self, parser):
        schema = self.get_schema()
        to_delete = [x for x in schema.keys() if "*" in x or "?" in x]
        for key in to_delete:
            orig = schema[key]
            del schema[key]
            for section in parser.sections():
                if fnmatch.fnmatch(section, key):
                    schema[section] = copy.deepcopy(orig)
        return schema

    def __get_public_schema(self, parser):
        schema = self.__get_schema(parser)
        public_schema = {}
        for section in schema.keys():
            if section.startswith('_'):
                continue
            if 'schema' not in schema[section]:
                continue
            public_schema[section] = \
                {x: y for x, y in schema[section].items() if x != "schema"}
            public_schema[section]['schema'] = {}
            for key in schema[section]['schema'].keys():
                if key.startswith('_'):
                    continue
                public_schema[section]['schema'][key] = \
                    schema[section]['schema'][key]
        return public_schema

    def _get_debug(self):
        self.load()
        res = {x: y for x, y in inspect.getmembers(self)
               if is_jsonable(y) and not x.startswith('_')
               and not x.startswith('raw_')}
        res["_doc"] = self._doc
        return res

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
        try:
            return self.get_final_document(vdocument)
        except BadPlugin:
            # we raise this exception
            raise
        except Exception:
            print("exception catched during get_final_document(), vdocument:",
                  file=sys.stderr)
            print(get_nice_dump(vdocument), file=sys.stderr)
            print("=> reraising", file=sys.stderr)
            raise

    def __validate(self, paths, public=False):
        v = Validator()
        v.allow_unknown = False
        v.require_all = True
        parser = OpinionatedConfigParser()
        try:
            parser.read(paths)
        except Exception:
            raise BadPlugin("can't read configuration paths: %s" %
                            ", ".join(paths))
        if public:
            schema = self.__get_public_schema(parser)
        else:
            schema = self.__get_schema(parser)
        status = validate_configparser(v, parser, schema, public=public)
        if status is False:
            return (status, v.errors, None)
        else:
            return (True, {}, v.document)

    def load(self):
        with PluginEnvContextManager(get_current_envs(self.plugin_name,
                                                      self.plugin_home)):
            if self.__loaded:
                return False
            self.__loaded = True
            status, vv_errors, v_document = self.__validate(self.paths)
            if status is False:
                if len(self.paths) == 1:
                    errors = cerberus_errors_to_human_string(vv_errors)
                    raise BadPlugin(
                        "invalid configuration file: %s" %
                        self._config_filepath,
                        validation_errors=errors)
                else:
                    # we are trying to find the bad file
                    status, v_errors, _ = \
                        self.__validate([self._config_filepath])
                    errors = cerberus_errors_to_human_string(v_errors)
                    raise BadPlugin(
                        "invalid configuration file: %s" %
                        self._config_filepath,
                        validation_errors=errors)
                    for p in self.paths:
                        if p == self._config_filepath:
                            continue
                        status, v_errors, _ = \
                            self.__validate([p], public=True)
                        if status is False:
                            errors = cerberus_errors_to_human_string(v_errors)
                            raise BadPlugin(
                                "invalid configuration, please fix: %s" % p,
                                validation_errors=errors)
                    errors = cerberus_errors_to_human_string(vv_errors)
                    candidates = " or ".join(self.paths)
                    raise BadPlugin(
                        "invalid configuration, please fix: %s" % candidates,
                        validation_errors=errors)
            self._doc = self.__get_final_document(v_document)
            self._apps = []
            self._extra_daemons = []
            # FIXME: step mfdata ?
            for section in [x for x in self._doc.keys()
                            if x.startswith("app_") or x.startswith("step_")]:
                c = self.app_class
                if section.startswith("app_"):
                    name = section[4:]
                elif section.startswith("step_"):
                    name = section[5:]
                else:
                    raise Exception("non handled case: %s" % section)
                command = c(self.plugin_home, self.plugin_name, name,
                            self._doc[section], self._doc.get('custom', {}))
                self.add_app(command)
            for section in [x for x in self._doc.keys()
                            if x.startswith("extra_daemon_")]:
                c = self.extra_daemon_class
                command = c(self.plugin_home,
                            self.plugin_name,
                            section.replace('extra_daemon_', '', 1),
                            self._doc[section],
                            self._doc.get('custom', {}))
                self.add_extra_daemon(command)
            self.after_load()

    def after_load(self):
        pass

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
    def steps(self):
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

    @property
    def add_plugin_dir_to_python_path(self):
        self.load()
        return self._doc['general']['_add_plugin_dir_to_python_path']
