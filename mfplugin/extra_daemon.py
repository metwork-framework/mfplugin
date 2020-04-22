from mfplugin.command import COMMAND_SCHEMA, Command

EXTRA_DAEMON_SCHEMA = {
    **COMMAND_SCHEMA
}


class ExtraDaemon(Command):

    def __init__(self, plugin_home, plugin_name, name, doc_fragment,
                 custom_fragment):
        Command.__init__(self, plugin_home, plugin_name, name, doc_fragment,
                         custom_fragment)
        self._type = "extra"
