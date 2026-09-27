"""Adapter for reading CardScheduler settings from Anki's add-on config."""

try:
    from aqt import mw
except ImportError:
    mw = None


def load_anki_addon_config(module_name, mw_instance=None):
    """Return Anki add-on config for this package, or None outside Anki."""
    anki_mw = mw if mw_instance is None else mw_instance
    addon_manager = getattr(anki_mw, "addonManager", None)
    if addon_manager is None:
        return None

    addon_module_name = _addon_module_name(module_name)
    config = addon_manager.getConfig(addon_module_name)
    if isinstance(config, dict):
        return config
    return None


def write_anki_addon_config(module_name, config, mw_instance=None):
    """Persist add-on configuration through Anki's add-on manager."""
    anki_mw = mw if mw_instance is None else mw_instance
    addon_manager = getattr(anki_mw, "addonManager", None)
    if addon_manager is None:
        raise RuntimeError("Anki's add-on manager is not available.")

    addon_manager.writeConfig(_addon_module_name(module_name), config)


def _addon_module_name(module_name):
    return module_name.split(".", 1)[0]
