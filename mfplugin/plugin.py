import os
import hashlib
from mflog import get_logger
from mfutil import BashWrapper
from mfplugin.configuration import Configuration
from mfplugin.command import Command
from mfplugin.utils import BadPlugin, get_default_plugins_base_dir, \
    get_rpm_cmd, NotInstalledPlugin, layerapi2_label_file_to_plugin_name

LOGGER = get_logger("mfplugin.py")


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
    configuration_class = None
    command_class = None
    plugins_base_dir = None

    def __init__(self, plugins_base_dir, name, home,
                 configuration_class=Configuration,
                 command_class=Command):
        self.configuration_class = configuration_class
        self.command_class = command_class
        self.name = name
        self.home = home
        if plugins_base_dir is not None:
            self.plugins_base_dir = plugins_base_dir
        else:
            self.plugins_base_dir = get_default_plugins_base_dir()
        self.__loaded = False

    @classmethod
    def make_from_directory(cls, plugins_base_dir, home,
                            configuration_class=Configuration,
                            command_class=Command):
        llfpath = os.path.join(home, ".layerapi2_label")
        name = layerapi2_label_file_to_plugin_name(llfpath)
        return cls(plugins_base_dir, name, home,
                   configuration_class=configuration_class,
                   command_class=command_class)

    def is_dev_linked(self):
        return os.path.islink(os.path.join(self.plugins_base_dir, self.name))

    def load(self):
        if self.__loaded is True:
            return
        c = self.configuration_class
        self._configuration = c(self.name, self.home,
                                command_class=self.command_class)
        self._load_format_version()
        self._load_version_release()
        self._load_rpm_infos()
        self.__loaded = True

    def _load_version_release(self):
        # maybe this is a devlinked plugin?
        if self.is_dev_linked():
            self._version = "devlink"
            self._release = "devlink"
            return
        frmt = "%{version}~~~%{release}\\n"
        cmd = get_rpm_cmd(self.plugins_base_dir, '-q',
                          '--qf "%s" %s' % (frmt, self.name))
        x = BashWrapper(cmd)
        if not x:
            raise NotInstalledPlugin()
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
        return res[0:3]

    def _load_rpm_infos(self):
        if self.is_dev_linked():
            self._raw_metadata_output = "DEV_LINK"
            self._raw_files_output = "DEV_LINK"
            self._files = []
            return
        cmd = get_rpm_cmd(self.plugins_base_dir, '-qi', '-p %s' % self.name)
        x = BashWrapper(cmd)
        if not x:
            raise NotInstalledPlugin()
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
        cmd = get_rpm_cmd(self.plugins_base_dir, '-ql -p %s' % self.name)
        x = BashWrapper(cmd)
        if not x:
            raise NotInstalledPlugin()
        self._files = [x.strip() for x in x.stdout.split('\n')]

    def get_hash(self):
        sid = ", ".join([self.build_host, self.build_date, self.size,
                        self.version, self.release])
        return hashlib.md5(sid.encode('utf8')).hexdigest()

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
