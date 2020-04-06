import os
from mfplugin.utils import NON_REQUIRED_INTEGER_DEFAULT_0, to_bool, \
    NON_REQUIRED_STRING_DEFAULT_EMPTY

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
    "graceful_timeout": NON_REQUIRED_INTEGER_DEFAULT_0,
    "max_age": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_as": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_nofile": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_stack": NON_REQUIRED_INTEGER_DEFAULT_0,
    "rlimit_fsize": NON_REQUIRED_INTEGER_DEFAULT_0
}


class Command(object):

    def __init__(self, plugin_name, doc_fragment):
        self.plugin_name = plugin_name
        self._doc_fragment = doc_fragment

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
