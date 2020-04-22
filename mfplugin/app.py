from mfplugin.command import COMMAND_SCHEMA, Command

APP_SCHEMA = {
    **COMMAND_SCHEMA
}


class App(Command):

    def __init__(self, plugin_home, plugin_name, name, doc_fragment,
                 custom_fragment):
        Command.__init__(self, plugin_home, plugin_name, name, doc_fragment,
                         custom_fragment)
        self._type = "app"
