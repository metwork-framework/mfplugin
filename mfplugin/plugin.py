import os
import hashlib
import envtpl
import shutil
import glob
from gitignore_parser import parse_gitignore
from mflog import get_logger
from mfutil import BashWrapper, get_unique_hexa_identifier, mkdir_p_or_die, \
    BashWrapperOrRaise
from mfutil.layerapi2 import LayerApi2Wrapper
from mfplugin.configuration import Configuration
from mfplugin.command import Command
from mfplugin.utils import BadPlugin, get_default_plugins_base_dir, \
    get_rpm_cmd, layerapi2_label_file_to_plugin_name, validate_plugin_name, \
    CantBuildPlugin, plugin_name_to_layerapi2_label

LOGGER = get_logger("mfplugin.py")
MFEXT_HOME = os.environ.get("MFEXT_HOME", None)
MFMODULE_RUNTIME_HOME = os.environ.get('MFMODULE_RUNTIME_HOME', '/tmp')
MFMODULE_LOWERCASE = os.environ.get('MFMODULE_LOWERCASE', 'generic')
MFMODULE = os.environ.get('MFMODULE', 'GENERIC')
SPEC_TEMPLATE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "plugin.spec")


class Plugin(object):

    __loaded = None
    _configuration = None
    name = None
    home = None
    _version = None
    _release = None
    _files = None
    _raw_metadata_output = None
    _raw_files_output = None
    _format_version = None
    _build_host = None
    _build_date = None
    _size = None
    _release_ignored_files = None
    configuration_class = None
    command_class = None
    plugins_base_dir = None
    is_dev_linked = None
    _is_installed = None

    def __init__(self, plugins_base_dir, home,
                 configuration_class=Configuration,
                 command_class=Command):
        self.configuration_class = configuration_class
        self.command_class = command_class
        self.home = os.path.abspath(home)
        if plugins_base_dir is not None:
            self.plugins_base_dir = plugins_base_dir
        else:
            self.plugins_base_dir = get_default_plugins_base_dir()
        self.name = self._get_name()
        self.is_dev_linked = os.path.islink(os.path.join(self.plugins_base_dir,
                                                         self.name))
        self.__loaded = False
        # FIXME: detect broken symlink

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
        self._configuration = c(self.name, self.home,
                                command_class=self.command_class)
        self._load_format_version()
        self._load_rpm_infos()
        self._load_version_release()
        self._load_release_ignored_files()

    def load_full(self):
        self.load()
        self.configuration.load()

    def get_plugin_env_dict(self, add_current_envs=True):
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
                home = LayerApi2Wrapper.get_layer_home(tmp)
                try:
                    p = Plugin(self.plugins_base_dir, home)
                    p.load()
                except Exception:
                    continue
                res.update(p.get_plugin_env_dict(add_current_envs=False))
        env_var_dict = self.configuration.get_configuration_env_dict(
            ignore_keys_starting_with="_", add_resolved=True)
        res.update(env_var_dict)
        if add_current_envs:
            res["%s_CURRENT_PLUGIN_NAME" % MFMODULE] = self.name
            res["%s_CURRENT_PLUGIN_DIR" % MFMODULE] = self.home
            res["%s_CURRENT_PLUGIN_LABEL" % MFMODULE] = \
                plugin_name_to_layerapi2_label(self.name)
        return res

    def set_plugin_env(self):
        env_var_dict = self.get_plugin_env_dict()
        for k, v in env_var_dict.items():
            os.environ[k] = v

    def _load_version_release(self):
        if not self._is_installed:
            # the plugin is not installed, let's read version in configuration
            self._version = self.configuration.version
            self._release = "1"
            return
        # the plugin is installed
        if self.is_dev_linked:
            # this is a devlink
            self._version = "devlink"
            self._release = "devlink"
            return
        frmt = "%{version}~~~%{release}\\n"
        cmd = get_rpm_cmd(self.plugins_base_dir, '-q',
                          '--qf "%s" %s' % (frmt, self.name))
        x = BashWrapper(cmd)
        if not x:
            raise Exception(x)
        if x:
            tmp = x.stdout.split('~~~')
            if len(tmp) < 2:
                raise Exception("incorrect output for cmd: %s" % cmd)
            self._version = tmp[0]
            self._release = tmp[1]

    def _load_format_version(self):
        pfv = os.path.join(self.home, ".plugin_format_version")
        if not os.path.isfile(pfv):
            raise BadPlugin("%s is missing" % pfv)
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

    def _load_release_ignored_files(self):
        self._release_ignored_files = []
        ignore_filepath = os.path.join(self.home, ".releaseignore")
        if os.path.isfile(ignore_filepath):
            matches = parse_gitignore(ignore_filepath)
            for r, d, f in os.walk(self.home):
                for flder in d:
                    if matches(os.path.join(self.home, r, flder)):
                        self._release_ignored_files.append(
                            os.path.relpath(os.path.join(r, flder),
                                            start=self.home)
                        )
                for fle in f:
                    if matches(os.path.join(self.home, r, fle)):
                        self._release_ignored_files.append(
                            os.path.relpath(os.path.join(r, fle),
                                            start=self.home)
                        )

    def _load_rpm_infos(self):
        if self.is_dev_linked:
            self._raw_metadata_output = "DEV_LINK"
            self._raw_files_output = "DEV_LINK"
            self._files = []
            self._is_installed = True
            return
        cmd = get_rpm_cmd(self.plugins_base_dir, '-qi', self.name)
        x = BashWrapper(cmd)
        if not x:
            self._is_installed = False
            return
        self._raw_metadata_output = x.stdout
        for line in x.stdout.split('\n'):
            tmp = line.strip().split(':', 1)
            if len(tmp) <= 1:
                continue
            name = tmp[0].strip().lower()
            value = tmp[1].strip()
            if name == "build host":
                self._build_host = value
            if name == "build date":
                self._build_date = value
            if name == "size":
                self._size = value
        cmd = get_rpm_cmd(self.plugins_base_dir, '-ql', self.name)
        x = BashWrapper(cmd)
        if not x:
            raise Exception(x)
        self._is_installed = True
        self._files = [x.strip() for x in x.stdout.split('\n')]

    def get_hash(self):
        sid = ", ".join([self.build_host, self.build_date, self.size,
                        self.version, self.release])
        return hashlib.md5(sid.encode('utf8')).hexdigest()

    def _make_plugin_spec(self, dest_file, name, version, summary, license,
                          packager, vendor, url, excludes):
        with open(SPEC_TEMPLATE, "r") as f:
            template = f.read()
        extra_vars = {"NAME": name, "VERSION": version, "SUMMARY": summary,
                      "LICENSE": license, "PACKAGER": packager,
                      "VENDOR": vendor, "URL": url, "EXCLUDES": excludes}
        res = envtpl.render_string(template, extra_variables=extra_vars,
                                   keep_multi_blank_lines=False)
        with open(dest_file, "w") as f:
            f.write(res)

    def build(self):
        self.load()
        base = os.path.join(self.plugins_base_dir, "base")
        pwd = os.getcwd()
        tmpdir = os.path.join(MFMODULE_RUNTIME_HOME, "tmp",
                              "plugin_%s" % get_unique_hexa_identifier())
        mkdir_p_or_die(os.path.join(tmpdir, "BUILD"))
        mkdir_p_or_die(os.path.join(tmpdir, "RPMS"))
        mkdir_p_or_die(os.path.join(tmpdir, "SRPMS"))
        config = self.configuration
        self._make_plugin_spec(
            os.path.join(tmpdir, "specfile.spec"),
            self.name, config.version,
            config.summary, config.license, config.packager,
            config.vendor, config.url, self.release_ignored_files
        )
        cmd = ""
        if MFEXT_HOME is not None:
            cmd = cmd + "source %s/lib/bash_utils.sh ; " % MFEXT_HOME
            cmd = cmd + "layer_load rpm@mfext ; "
        cmd = cmd + 'rpmbuild --define "_topdir %s" --define "pwd %s" ' \
            '--define "prefix %s" --dbpath %s ' \
            '-bb %s/specfile.spec' % (tmpdir, self.home, tmpdir,
                                      base, tmpdir)
        x = BashWrapperOrRaise(cmd, CantBuildPlugin,
                               "can't build plugin %s" % self.home)
        tmp = glob.glob(os.path.join(tmpdir, "RPMS", "x86_64", "*.rpm"))
        if len(tmp) == 0:
            raise CantBuildPlugin("can't find generated plugin" %
                                  self.home, bash_wrapper=x)
        plugin_path = tmp[0]
        new_basename = \
            os.path.basename(plugin_path).replace("x86_64.rpm",
                                                  "metwork.%s.plugin" %
                                                  MFMODULE_LOWERCASE)
        new_plugin_path = os.path.join(pwd, new_basename)
        shutil.move(plugin_path, new_plugin_path)
        shutil.rmtree(tmpdir, True)
        os.chdir(pwd)
        return new_plugin_path

    @property
    def configuration(self):
        self.load()
        return self._configuration

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
    def release_ignored_files(self):
        self.load()
        return self._release_ignored_files
