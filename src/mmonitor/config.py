from os.path import dirname, abspath, join

_MMONITOR_ROOT = dirname(abspath(__file__))
_RESOURCES = join(_MMONITOR_ROOT, 'resources')

mmonitor_db_path = join(_RESOURCES, 'mmonitor.db')
