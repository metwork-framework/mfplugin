import os
from mfplugin.utils import NON_REQUIRED_INTEGER_DEFAULT_0, to_bool, \
    NON_REQUIRED_STRING_DEFAULT_EMPTY, NON_REQUIRED_BOOLEAN_DEFAULT_FALSE, \
    NON_REQUIRED_INTEGER

__pdoc__ = {
    "coerce_log_split_stdout_sterr": False,
    "coerce_log_split_multiple_workers": False
}


def coerce_log_split_stdout_sterr(val):
    if val == "AUTO":
        return to_bool(
            os.environ["%s_LOG_TRY_TO_SPLIT_STDOUT_STDERR" % MFMODULE])
    return to_bool(val)


def coerce_log_split_multiple_workers(val):
    if val == "AUTO":
        return to_bool(
            os.environ["%s_LOG_TRY_TO_SPLIT_MULTIPLE_WORKERS" % MFMODULE])
    return to_bool(val)


MFMODULE = os.environ.get("MFMODULE", "GENERIC")
MFMODULE_RUNTIME_HOME = os.environ.get("MFMODULE_RUNTIME_HOME", "/tmp")
COMMAND_SCHEMA = {
    "log_split_stdout_stderr": {
        "required": False,
        "type": "boolean",
        "default": "AUTO",
        "coerce": (str, coerce_log_split_stdout_sterr),
    },
    "log_split_multiple_workers": {
        "required": False,
        "type": "boolean",
        "default": "AUTO",
        "coerce": (str, coerce_log_split_multiple_workers),
    },
    "numprocesses": NON_REQUIRED_INTEGER_DEFAULT_0,
    "_cmd_and_args": NON_REQUIRED_STRING_DEFAULT_EMPTY,
    "graceful_timeout": {
        **NON_REQUIRED_INTEGER,
        "default": 10
    },
    "max_age": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_as": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_nofile": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_stack": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_fsize": NON_REQUIRED_INTEGER_DEFAULT_0,
    "debug": NON_REQUIRED_BOOLEAN_DEFAULT_FALSE
}


class Command(object):

    def __init__(self, plugin_home, plugin_name, name, doc_fragment,
                 custom_fragment):
        self.plugin_name = plugin_name
        self.plugin_home = plugin_home
        self._doc_fragment = doc_fragment
        self._custom_fragment = custom_fragment
        self.name = name
        self._type = "command"

    def duplicate(self, new_name=None):
        c = self.__class__
        if new_name is None:
            new_name = self.name
        return c(self.plugin_home, self.plugin_name, new_name,
                 dict(self._doc_fragment), dict(self._custom_fragment))

    @property
    def cmd_and_args(self):
        return self._doc_fragment["_cmd_and_args"]

    @property
    def numprocesses(self):
        return self._doc_fragment["numprocesses"]

    @property
    def log_split_stdout_stderr(self):
        return self._doc_fragment["log_split_stdout_stderr"]

    @property
    def log_split_multiple_workers(self):
        return self._doc_fragment["log_split_multiple_workers"]

    @property
    def graceful_timeout(self):
        return self._doc_fragment["graceful_timeout"]

    @property
    def max_age(self):
        return self._doc_fragment["max_age"]

    @property
    def rlimit_as(self):
        return self._doc_fragment["rlimit_as"]

    @property
    def rlimit_nofile(self):
        return self._doc_fragment["rlimit_nofile"]

    @property
    def rlimit_stack(self):
        return self._doc_fragment["rlimit_stack"]

    @property
    def rlimit_fsize(self):
        return self._doc_fragment["rlimit_fsize"]

    @property
    def debug(self):
        return self._doc_fragment["debug"]

    def _get_log_proxy_args(self):
        if self.log_split_multiple_workers and self.numprocesses > 1:
            std_prefix = f"{MFMODULE_RUNTIME_HOME}/log/" \
                f"{self._type}_{self.plugin_name}_{self.name}_" \
                "worker$(circus.wid)"
        else:
            std_prefix = f"{MFMODULE_RUNTIME_HOME}/log/" \
                f"{self._type}_{self.plugin_name}_{self.name}"
        if self.numprocesses <= 1:
            use_locks = ""
        else:
            use_locks = "--use-locks"
        if self.log_split_stdout_stderr:
            res = "%s --stdout %s.stdout " \
                "--stderr %s.stderr" % (use_locks, std_prefix, std_prefix)
        else:
            res = "%s --stdout %s.log " \
                "--stderr STDOUT" % (use_locks, std_prefix)
        return res

    @property
    def circus_cmd_and_args(self):
        res = "%s -- plugin_wrapper %s -- %s" % \
            (self._get_log_proxy_args(),
             self.plugin_name,
             self.cmd_and_args)
        res = res.replace("{plugin_name}", self.plugin_name)
        res = res.replace("{plugin_dir}", self.plugin_home)
        res = res.replace("{%s_name}" % self._type, self.name)
        return res

    @property
    def type(self):
        return self._type
