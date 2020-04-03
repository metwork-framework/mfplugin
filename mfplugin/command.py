import os
from mfplugin.utils import to_bool


def coerce_log_split_stdout_sterr(val):
    if val == "AUTO":
        return to_bool(
            os.environ["%s_LOG_TRY_TO_SPLIT_STDOUT_STDERR" % MFMODULE])
    return to_bool(val)


def coerce_log_split_multiple_workers(val):
    if val == "AUTO":
        return to_bool(
            os.environ["%s_LOG_SPLIT_MULTIPLE_WORKERS" % MFMODULE])
    return to_bool(val)


MFMODULE = os.environ.get("MFMODULE", "GENERIC")
NON_REQUIRED_DEFAULT_0_INTEGER = {
    "required": False,
    "type": "integer",
    "default": 0,
    "coerce": int
}
COMMAND_SCHEMA = {
    "log_split_stdout_stderr": {
        "required": False,
        "type": "string",
        "allowed": ["1", "0", "AUTO"],
        "default": "AUTO",
        "coerce": (str, coerce_log_split_stdout_sterr),
    },
    "log_split_multiple_workers": {
        "required": False,
        "type": "string",
        "allowed": ["1", "0", "AUTO"],
        "default": "AUTO",
        "coerce": (str, coerce_log_split_multiple_workers),
    },
    "numprocesses": {"required": True, "type": "integer", "coerce": int},
    "_cmd_and_args": {"required": True, "type": "string", "minlength": 1},
    "graceful_timeout": NON_REQUIRED_DEFAULT_0_INTEGER,
    "max_age": NON_REQUIRED_DEFAULT_0_INTEGER,
    "rlimit_as": NON_REQUIRED_DEFAULT_0_INTEGER,
    "rlimit_nofile": NON_REQUIRED_DEFAULT_0_INTEGER,
    "rlimit_stack": NON_REQUIRED_DEFAULT_0_INTEGER,
    "rlimit_fsize": NON_REQUIRED_DEFAULT_0_INTEGER
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
