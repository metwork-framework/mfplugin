import os
import tarfile
import json
from mfplugin.utils import get_default_plugins_base_dir, \
    BadPluginFile, layerapi2_label_to_plugin_name


class PluginFile(object):

    def __init__(self, plugin_filepath):
        self.plugins_base_dir = get_default_plugins_base_dir()
        """Plugins base directory (string)."""
        if not os.path.isfile(plugin_filepath):
            raise BadPluginFile("file: %s not found" % plugin_filepath)
        self.plugin_filepath = plugin_filepath
        """Plugin file path (string)."""
        self.__loaded = False

    def load(self):
        if self.__loaded:
            return
        self.__loaded = True
        if not os.path.isfile(self.plugin_filepath):
            raise BadPluginFile("%s does not exist" % self.plugin_filepath)
        try:
            tf = tarfile.open(name=self.plugin_filepath, mode='r')
        except Exception as e:
            raise BadPluginFile(
                "can't open %s as a tar.gz file => this is probably not a "
                "metwork >= 1.0 plugin" % self.plugin_filepath,
                original_exception=e)
        try:
            reader1 = tf.extractfile("metwork_plugin/.layerapi2_label")
            label = reader1.read().decode('utf8').strip()
            self._name = layerapi2_label_to_plugin_name(label)
        except Exception as e:
            raise BadPluginFile(
                "can't read/find metwork_plugin/.layerapi2_label file in "
                "plugin", original_exception=e)
        try:
            reader2 = tf.extractfile("metwork_plugin/.metadata.json")
            metadata = json.loads(reader2.read().decode('utf8').strip())
            self._version = metadata['version']
            self._release = metadata['release']
            self._build_host = metadata['build_host']
            self._build_date = metadata['build_date']
            self._size = metadata['size']
            self._summary = metadata['summary']
            self._license = metadata['license']
            self._packager = metadata['packager']
            self._vendor = metadata['vendor']
            self._url = metadata['url']
        except Exception as e:
            raise BadPluginFile(
                "can't read/find metwork_plugin/.metadata.json file in "
                "plugin", original_exception=e)
        try:
            reader3 = tf.extractfile("metwork_plugin/.files.json")
            self._files = json.loads(reader3.read().decode('utf8').strip())
        except Exception as e:
            raise BadPluginFile(
                "can't read/find metwork_plugin/.files.json file in "
                "plugin", original_exception=e)

    @property
    def summary(self):
        self.load()
        return self._summary

    @property
    def license(self):
        self.load()
        return self._license

    @property
    def packager(self):
        self.load()
        return self._packager

    @property
    def name(self):
        self.load()
        return self._name

    @property
    def vendor(self):
        self.load()
        return self._vendor

    @property
    def url(self):
        self.load()
        return self._url

    @property
    def version(self):
        self.load()
        return self._version

    @property
    def release(self):
        self.load()
        return self._release

    @property
    def size(self):
        self.load()
        return self._size

    @property
    def build_host(self):
        self.load()
        return self._build_host

    @property
    def build_date(self):
        self.load()
        return self._build_date

    @property
    def files(self):
        self.load()
        return self._files

    @property
    def home(self):
        return None
