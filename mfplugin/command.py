import os
from mfplugin.utils import get_plugin_env, BadPluginConfiguration

MFMODULE = os.environ.get("MFMODULE", "GENERIC")
COMMAND_SCHEMA = {
    "log_split_stdout_stderr": {"required": False, "type": "string",
                                "allowed": ["1", "0", "AUTO"]},
    "log_split_multiple_workers": {"required": False, "type": "string",
                                   "allowed": ["1", "0", "AUTO"]},
    "numprocesses": {"required": True, "type": "integer"},
    "_cmd_and_args": {"required": True, "type": "string", "minlength": 1},
    "graceful_timeout": {"required": False, "type": "integer"},
    "max_age": {"required": False, "type": "integer"},
    "rlimit_as": {"required": False, "type": "integer"},
    "rlimit_nofile": {"required": False, "type": "integer"},
    "rlimit_stack": {"required": False, "type": "integer"},
    "rlimit_fsize": {"required": False, "type": "integer"},
}


class Command(object):

    __loaded = False
    _plugin_name = None
    _parser = None
    _section = None
    _cmd_and_args = None
    _numprocesses = None
    _log_split_stdout_stderr = None
    _log_split_multiple_workers = None
    _max_age = None
    _graceful_timeout = None
    _rlimit_as = None
    _rlimit_nofile = None
    _rlimit_stack = None
    _rlimit_fsize = None

    def __init__(self, plugin_name, parser, section):
        self._plugin_name = plugin_name
        self._parser = parser
        self._section = section

    def _get_env(self, key, default=None, normalize_func=lambda x: x):
        env = get_plugin_env(self._plugin_name, self._section, key)
        tmp = os.environ.get(env, default)
        if tmp is not None:
            tmp = normalize_func(tmp)
        return tmp

    def load(self):
        if self.__loaded:
            return
        self.__loaded = True
        self._cmd_and_args = \
            self._parser.get(self._section, "cmd_and_args")
        self._numprocesses = self._get_env("numprocesses", "1", int)
        self._log_split_stdout_stderr = False
        tmp = self._get_env("log_split_stdout_stderr", "AUTO")
        if tmp == "AUTO":
            global_conf = \
                os.environ["%s_LOG_TRY_TO_SPLIT_STDOUT_STDERR" % MFMODULE]
            self._log_split_stdout_stderr = (global_conf == "1")
        elif tmp == "1":
            self._log_split_stdout_stderr = True
        elif tmp == "0":
            self._log_split_stdout_stderr = False
        else:
            raise BadPluginConfiguration(
                "invalid value for log_split_stdout_stderr: %s" % tmp)
        self._log_split_multiple_workers = False
        tmp = self._get_env("log_split_multiple_workers", "AUTO")
        if tmp == "AUTO":
            global_conf = \
                os.environ["%s_LOG_SPLIT_MULTIPLE_WORKERS" % MFMODULE]
            self._log_split_multiple_workers = (global_conf == "1")
        elif tmp == "1":
            self._log_split_multiple_workers = True
        elif tmp == "0":
            self._log_split_multiple_workers = False
        else:
            raise BadPluginConfiguration(
                "invalid value for log_split_multiple_workers: %s" % tmp)
        self._mag_age = self._get_env("max_age", "0", int)
        self._graceful_timeout = self._get_env("graceful_timeout", 10, int)
        self._rlimit_as = self._get_env("rlimit_as", None, int)
        self._rlimit_nofile = self._get_env("rlimit_nofile", None, int)
        self._rlimit_stack = self._get_env("rlimit_stack", None, int)
        self._rlimit_fsize = self._get_env("rlimit_fsize", None, int)

    @property
    def cmd_and_args(self):
        self.load()
        return self._cmd_and_args

    @property
    def numprocesses(self):
        self.load()
        return self._numprocesses

    @property
    def log_split_stdout_stderr(self):
        self.load()
        return self._log_split_stdout_stderr

    @property
    def log_split_multiple_workers(self):
        self.load()
        return self._log_split_multiple_workers

    @property
    def max_age(self):
        self.load()
        return self._max_age

    @property
    def graceful_timeout(self):
        self.load()
        return self._graceful_timeout

    @property
    def rlimit_as(self):
        self.load()
        return self._rlimit_as

    @property
    def rlimit_nofile(self):
        self.load()
        return self._rlimit_nofile

    @property
    def rlimit_stack(self):
        self.load()
        return self._rlimit_stack

    @property
    def rlimit_fsize(self):
        self.load()
        return self._rlimit_fsize
