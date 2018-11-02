"""BLE/LSL interfacing parameters for specific devices.

TODO:
    * Simple class (or specification/template) for device parameters
"""

import pkgutil

DEVICE_NAMES = []
"""(Module) names for all compatible devices.

Assigned below; all top-level modules in this directory (except 'device')
are included.
"""

# `from ble2lsl.devices import *` will import all available device files
# useful for testing; should not be used in production
__all__ = []
for loader, module_name, is_pkg in pkgutil.walk_packages(__path__):
    if module_name != 'device' and '.' not in module_name:
        __all__.append(module_name)
        DEVICE_NAMES.append(module_name)
        module = loader.find_module(module_name).load_module(module_name)
        globals()[module_name] = module
