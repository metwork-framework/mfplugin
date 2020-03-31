from .plugin import MFPlugin
from .plugin_configuration import MFPluginConfiguration
from .plugin_command import MFPluginCommand


class MFPluginsManager(object):

    plugin_class = None
    plugin_configuration_class = None
    plugin_command_class = None

    def __init__(self, plugins_base_dir=None, plugin_class=MFPlugin,
                 plugin_configuration_class=MFPluginConfiguration,
                 plugin_command_class=MFPluginCommand):
        self.plugin_class = plugin_class
        self.plugin_configuration_class = plugin_configuration_class
        self.plugin_command_class = plugin_command_class
