import os
import hashlib
import json
import datetime
import pickle
from pathlib import Path
import inspect
import shutil
import socket
from gitignore_parser import parse_gitignore
from mfutil import BashWrapper, get_unique_hexa_identifier, mkdir_p_or_die, \
    mkdir_p, BashWrapperOrRaise, hash_generator
from mfplugin.configuration import Configuration
from mfplugin.app import App
from mfplugin.extra_daemon import ExtraDaemon
from mfplugin.utils import BadPlugin, get_default_plugins_base_dir, \
    layerapi2_label_file_to_plugin_name, validate_plugin_name, \
    CantBuildPlugin, get_current_envs, PluginEnvContextManager, \
    get_configuration_class, get_app_class, get_extra_daemon_class, \
    get_configuration_paths, \
    is_jsonable, layerapi2_label_to_plugin_home, plugin_name_to_layerapi2_label

MFEXT_HOME = os.environ.get("MFEXT_HOME", None)
MFMODULE_RUNTIME_HOME = os.environ.get('MFMODULE_RUNTIME_HOME', '/tmp')
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'generic')
MFMODULE = os.environ.get('MFMODULE', 'GENERIC')
SPEC_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "plugin.spec")
BUID_HOST = os.environ.get('MFHOSTNAME_FULL', socket.gethostname())


class Plugin(object):

    def __init__(self, plugins_base_dir, home,
                 configuration_class=None,
                 extra_daemon_class=None,
                 app_class=None,
                 dont_read_config_overrides=False):
        self.configuration_class = get_configuration_class(configuration_class,
                                                           Configuration)
        """Configuration class."""
        self.app_class = get_app_class(app_class, App)
        """App class."""
        self.extra_daemon_class = get_extra_daemon_class(extra_daemon_class,
                                                         ExtraDaemon)
        """Extra Daemon class."""
        self.home = os.path.abspath(home)
        """Plugin home (absolute and normalized string)."""
        self.plugins_base_dir = plugins_base_dir \
            if plugins_base_dir is not None else get_default_plugins_base_dir()
        """Plugin base directory (string)."""
        self.name = self._get_name()
        """Plugin name (string)."""
        self.is_dev_linked = os.path.islink(os.path.join(self.plugins_base_dir,
                                                         self.name))
        """Is the plugin a devlink? (boolean)."""
        self._dont_read_config_overrides = dont_read_config_overrides
        self._metadata = {}
        self._files = None
        self.__loaded = False
        # FIXME: detect broken symlink

    def _get_debug(self):
        self.load()
        self._load_files()  # as it is not included in load() for perfs reasons
        res = {x: y for x, y in inspect.getmembers(self)
               if is_jsonable(y) and not x.startswith('_')}
        res['configuration'] = self.configuration._get_debug()
        return res

    def _get_name(self):
        llfpath = os.path.join(self.home, ".layerapi2_label")
        tmp = layerapi2_label_file_to_plugin_name(llfpath)
        validate_plugin_name(tmp)
        return tmp

    def load(self):
        if self.__loaded is True:
            return
        self.__loaded = True
        c = self.configuration_class
        self._configuration = c(
            self.name, self.home,
            app_class=self.app_class,
            extra_daemon_class=self.extra_daemon_class,
            dont_read_config_overrides=self._dont_read_config_overrides
        )
        self._layerapi2_layer_name = plugin_name_to_layerapi2_label(self.name)
        self._load_format_version()
        self._load_metadata()
        self._load_version_release()
        # self._load_files() is not included here for perfs reasons

    def load_full(self):
        self.load()
        self.configuration.load()

    def reload(self):
        self.__loaded = False
        self.load()

    def _load_metadata(self):
        if self.is_dev_linked:
            self._is_installed = True
            self._build_host = "unknown"
            self._build_date = "unknown"
            self._size = "unknown"
            return
        metadata_filepath = "%s/%s/.metadata.json" % (self.plugins_base_dir,
                                                      self.name)
        self._is_installed = os.path.isfile(metadata_filepath)
        if self._is_installed:
            try:
                with open(metadata_filepath, "r") as f:
                    c = f.read().strip()
            except Exception as e:
                raise BadPlugin("can't read %s file" % metadata_filepath,
                                original_exception=e)
            try:
                self._metadata = json.loads(c)
            except Exception as e:
                raise BadPlugin("can't decode %s file" % metadata_filepath,
                                original_exception=e)
        self._build_host = self._metadata.get("build_host", "unknown")
        self._build_date = self._metadata.get("build_date", "unknown")
        self._size = self._metadata.get("size", "unknown")

    def get_configuration_hash(self):
        args = []
        try:
            with open("%s/.layerapi2_dependencies" % self.home, "r") as f:
                args.append(f.read())
        except Exception:
            pass
        for path in get_configuration_paths(self.name, self.home) \
                    + ["/etc/metwork.config"]:
            try:
                with open(path, "r") as f:
                    args.append(f.read())
            except Exception:
                pass
        return hash_generator(*args)

    def get_plugin_env_dict(self, add_current_envs=True,
                            set_tmp_dir=True,
                            cache=False):
        res = self._get_plugin_env_dict(add_current_envs=add_current_envs,
                                        set_tmp_dir=set_tmp_dir,
                                        cache=cache)
        # this bloc is here and not inside _get_plugin_env_dict because
        # PYTHONPATH shouldn't be cached (because it depends on loaded layers)
        if self.configuration.add_plugin_dir_to_python_path:
            old_python_path = os.environ.get("PYTHONPATH", None)
            if old_python_path:
                res["PYTHONPATH"] = self.home + ":" + old_python_path
            else:
                res["PYTHONPATH"] = self.home
        return res

    def _get_plugin_env_dict(self, add_current_envs=True,
                             set_tmp_dir=True,
                             cache=False):
        if cache:
            if not set_tmp_dir or not add_current_envs:
                raise Exception(
                    "cache=True is not compatible with add_current_envs=False "
                    "or set_tmp_dir=False")
            try:
                with open("%s/.configuration_cache" % self.home, "rb") as f:
                    h, res = pickle.loads(f.read())
                    if h == self.get_configuration_hash():
                        res["%s_CURRENT_PLUGIN_CACHE" % MFMODULE] = "1"
                        tmpdir = res["TMPDIR"]
                        if tmpdir != "" and not os.path.exists(tmpdir):
                            mkdir_p(tmpdir, nodebug=True, nowarning=True)
                        return res
            except Exception:
                pass
        lines = []
        res = {}
        try:
            # FIXME: shoud be better to parse this file in layerapi2
            with open("%s/.layerapi2_dependencies" % self.home, "r") as f:
                lines = f.readlines()
        except Exception:
            pass
        for line in lines:
            tmp = line.strip()
            if tmp.startswith('-'):
                tmp = tmp[1:]
            if tmp.startswith("plugin_"):
                home = layerapi2_label_to_plugin_home(self.plugins_base_dir,
                                                      tmp)
                if home is None:
                    continue
                try:
                    p = Plugin(self.plugins_base_dir, home)
                    p.load()
                except Exception:
                    continue
                res.update(p.get_plugin_env_dict(add_current_envs=False))
        env_var_dict = self.configuration.get_configuration_env_dict(
            ignore_keys_starting_with="_")
        res.update(env_var_dict)
        if add_current_envs:
            res.update(get_current_envs(self.name, self.home))
        if set_tmp_dir:
            tmpdir = os.path.join(MFMODULE_RUNTIME_HOME, "tmp", self.name)
            if mkdir_p(tmpdir, nodebug=True, nowarning=True):
                res["TMPDIR"] = tmpdir
        if cache:
            h = self.get_configuration_hash()
            tmpname = "%s/.configuration_cache.%s" % \
                (self.home, get_unique_hexa_identifier())
            with open(tmpname, "wb") as f:
                f.write(pickle.dumps([h, res]))
            os.rename(tmpname, "%s/.configuration_cache" % self.home)
            Path('%s/.configuration_cache' % self.home).touch()
        return res

    def plugin_env_context(self, **kwargs):
        return PluginEnvContextManager(self.get_plugin_env_dict(**kwargs))

    def _load_version_release(self):
        if not self._is_installed:
            # the plugin is not installed, let's read version in configuration
            self._version = self.configuration.version
            if self.configuration.release:
                self._release = self.configuration.release
            else:
                self._release = "1"
            return
        # the plugin is installed
        if self.is_dev_linked:
            # this is a devlink
            self._version = "dev_link"
            self._release = "dev_link"
            return
        self._version = self._metadata["version"]
        self._release = self._metadata["release"]

    def _load_format_version(self):
        pfv = os.path.join(self.home, ".plugin_format_version")
        if not os.path.isfile(pfv):
            raise BadPlugin("%s is missing => this is probably an old and "
                            "incompatible plugin => please migrate it!" % pfv)
        try:
            with open("%s/.plugin_format_version" % self.home, "r") as f:
                c = f.read().strip()
            tmp = c.split('.')
            if len(tmp) < 3:
                raise Exception()
        except Exception:
            raise BadPlugin("bad %s/.plugin_format_version format!" %
                            self.home)
        res = []
        for t in tmp:
            try:
                res.append(int(t))
            except Exception:
                res.append(9999)
        self._format_version = res[0:3]

    def print_dangerous_state(self):
        res = BashWrapper("_plugins.is_dangerous %s" % (self.name,))
        if res and res.stdout and len(res.stdout) > 0:
            print(res.stdout)

    def get_hash(self):
        sid = ", ".join([self.build_host, self.build_date, self.size,
                        self.version, self.release])
        return hashlib.md5(sid.encode('utf8')).hexdigest()

    def repackage(self):
        self.load()
        tmpdir = os.path.join(MFMODULE_RUNTIME_HOME, "tmp",
                              "plugin_%s" % get_unique_hexa_identifier())
        mkdir_p_or_die(tmpdir)
        shutil.copytree(self.home, os.path.join(tmpdir, "metwork_plugin"),
                        symlinks=True)

    def build(self):
        self.load()
        pwd = os.getcwd()
        tmpdir = os.path.join(MFMODULE_RUNTIME_HOME, "tmp",
                              "plugin_%s" % get_unique_hexa_identifier())
        filename = f"{self.name}-{self.version}-{self.release}." \
            f"metwork.{MFMODULE_LOWERCASE}.plugin"
        mkdir_p_or_die(tmpdir)
        shutil.copytree(self.home, os.path.join(tmpdir, "metwork_plugin"),
                        symlinks=True)
        matches = None
        ignore_filepath = os.path.join(self.home, ".releaseignore")
        if os.path.isfile(ignore_filepath):
            try:
                matches = parse_gitignore(ignore_filepath)
            except Exception as e:
                raise BadPlugin("bad %s file" % ignore_filepath,
                                original_exception=e)
        root = os.path.join(tmpdir, "metwork_plugin")
        if matches is not None:
            for r, d, f in os.walk(root, topdown=False):
                for fle in f:
                    full_path = os.path.join(r, fle)
                    path = self.home + full_path[len(root):]
                    if matches(path):
                        try:
                            os.unlink(full_path)
                        except Exception:
                            pass
                for flder in d:
                    full_path = os.path.join(r, flder)
                    path = self.home + full_path[len(root):]
                    if matches(path) and not os.listdir(full_path):
                        shutil.rmtree(full_path, ignore_errors=True)
        files = []
        total_size = 0
        for r, d, f in os.walk(os.path.join(tmpdir, "metwork_plugin")):
            for fle in f:
                path = os.path.join(r, fle)
                files.append("metwork_plugin/" + path[len(root) + 1:])
                if not os.path.islink(path):
                    total_size = total_size + os.path.getsize(path)
        with open("%s/metwork_plugin/.files.json" % tmpdir, "w") as f:
            f.write(json.dumps(files, indent=4))
        metadata = {
            "version": self.version,
            "release": self.release,
            "build_host": BUID_HOST,
            "build_date": datetime.datetime.utcnow().isoformat()[0:19] + 'Z',
            "size": str(total_size),
            "summary": self.configuration.summary,
            "license": self.configuration.license,
            "packager": self.configuration.packager,
            "vendor": self.configuration.vendor,
            "url": self.configuration.url
        }
        with open("%s/metwork_plugin/.metadata.json" % tmpdir, "w") as f:
            f.write(json.dumps(metadata, indent=4))
        plugin_path = os.path.abspath(f"{pwd}/{filename}")
        cmd = f"cd {tmpdir} && tar -cvf plugin.tar metwork_plugin && " \
            f"gzip -f plugin.tar && " \
            f"mv plugin.tar.gz {plugin_path}"
        BashWrapperOrRaise(cmd, CantBuildPlugin)
        if not os.path.isfile(plugin_path):
            raise CantBuildPlugin("can't find plugin file: %s" % plugin_path)
        shutil.rmtree(tmpdir, True)
        return plugin_path

    def _load_files(self):
        if self._files is not None:
            return
        if self.is_dev_linked:
            self._files = []
            return
        if not self.is_installed:
            self._files = []
            return
        filepath = "%s/%s/.files.json" % (self.plugins_base_dir, self.name)
        if not os.path.isfile(filepath):
            raise BadPlugin("%s is missing" % filepath)
        try:
            with open(filepath, "r") as f:
                c = f.read().strip()
        except Exception as e:
            raise BadPlugin("can't read %s file" % filepath,
                            original_exception=e)
        try:
            self._files = json.loads(c)
        except Exception as e:
            raise BadPlugin("can't decode %s file" % filepath,
                            original_exception=e)

    @property
    def configuration(self):
        self.load()
        return self._configuration

    @property
    def layerapi2_layer_name(self):
        self.load()
        return self._layerapi2_layer_name

    @property
    def format_version(self):
        self.load()
        return self._format_version

    @property
    def version(self):
        self.load()
        return self._version

    @property
    def release(self):
        self.load()
        return self._release

    @property
    def build_host(self):
        self.load()
        return self._build_host

    @property
    def build_date(self):
        self.load()
        return self._build_date

    @property
    def size(self):
        self.load()
        return self._size

    @property
    def is_installed(self):
        self.load()
        return self._is_installed

    @property
    def files(self):
        self.load()
        self._load_files()  # not included in load() for perfs reasons
        return self._files
