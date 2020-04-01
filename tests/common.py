import os
import shutil
from mfutil import mkdir_p_or_die

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))
BASE = os.path.join(CURRENT_DIR, "tmp", "plugins_base_dir")


def with_empty_base(func):
    def wrapper(*args, **kwargs):
        shutil.rmtree(BASE, True)
        mkdir_p_or_die(BASE)
        func(*args, **kwargs)
        shutil.rmtree(BASE, True)
    return wrapper


def unset_env():
    for env in ('MFMODULE_RUNTIME_HOME', 'MFMODULE', 'MFEXT_HOME',
                'MFMODULE_LOWERCASE'):
        try:
            del os.environ[env]
        except Exception:
            pass


unset_env()
