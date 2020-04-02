import os


for env in ('MFMODULE_RUNTIME_HOME', 'MFMODULE', 'MFEXT_HOME',
            'MFMODULE_LOWERCASE'):
    try:
        del os.environ[env]
    except KeyError:
        pass
