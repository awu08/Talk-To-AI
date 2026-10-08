"""API Keys: Each provider remembers its own keys, with optional named extras.

Every provider (Claude, ChatGPT, Gemini) has a "Primary" key, so switching
provider in Settings swaps to that provider's key automatically. You can add
more keys with your own names (for example "Work" or "School") and pick
which one is active for each provider.

Stored in settings.json under "api":
    "keys":        {"Claude": {"Primary": "sk-…", "Work": "sk-…"}, "Gemini": {…}}
    "active_keys": {"Claude": "Work", "Gemini": "Primary"}
    "api_key":     the active key for the current provider (kept for older code)

Settings saved by older versions (a single "api_key") are moved into the
current provider's Primary key the first time this module reads them.

Author: Allen Wu
Version: 1.1.0
"""

from typing import Dict, List

PRIMARY: str = "Primary"
MAX_NAME_LENGTH: int = 40


def _keys(config) -> Dict[str, Dict[str, str]]:
    ensure_migrated(config)
    return config.get("api", "keys") or {}


def _active(config) -> Dict[str, str]:
    return config.get("api", "active_keys") or {}


def ensure_migrated(config) -> None:
    """Move a single old-style api_key into the current provider's Primary key."""
    if config.get("api", "keys") is not None:
        return
    keys: Dict[str, Dict[str, str]] = {}
    provider = config.get("api", "provider") or ""
    old_key = config.get("api", "api_key") or ""
    if provider and old_key:
        keys[provider] = {PRIMARY: old_key}
    config.set("api", "keys", keys)
    config.set("api", "active_keys", {})


def names(config, provider: str) -> List[str]:
    """Key names for a provider, Primary first."""
    if not provider:
        return []
    others = [name for name in _keys(config).get(provider, {}) if name != PRIMARY]
    return [PRIMARY] + others


def active_name(config, provider: str) -> str:
    """The name of the key in use for a provider (Primary unless another was picked)."""
    name = _active(config).get(provider, PRIMARY)
    return name if name in names(config, provider) else PRIMARY


def get_key(config, provider: str, name: str) -> str:
    return _keys(config).get(provider, {}).get(name, "")


def active_key(config, provider: str) -> str:
    """The key the app should use for a provider right now.

    If the chosen key is empty, a key typed directly into settings.json as
    "api_key" is used for the current provider, so hand-edited settings work.
    """
    key = get_key(config, provider, active_name(config, provider))
    if not key and provider and provider == config.get("api", "provider"):
        key = config.get("api", "api_key") or ""
    return key


def _save(config, keys: Dict[str, Dict[str, str]], active: Dict[str, str]) -> None:
    config.set("api", "keys", keys)
    config.set("api", "active_keys", active)
    # Mirror the current provider's active key for code that reads api.api_key
    current = config.get("api", "provider") or ""
    config.set("api", "api_key", keys.get(current, {}).get(active.get(current, PRIMARY), "")
               if current else "")


def set_key(config, provider: str, name: str, value: str) -> None:
    """Save the key text for one named key."""
    if not provider:
        return
    keys = _keys(config)
    provider_keys = dict(keys.get(provider, {}))
    if provider_keys.get(name, "") == value and name in provider_keys:
        return
    provider_keys.setdefault(PRIMARY, "")
    provider_keys[name] = value
    keys = {**keys, provider: provider_keys}
    _save(config, keys, _active(config))


def set_active(config, provider: str, name: str) -> None:
    """Choose which named key a provider uses."""
    if provider and name in names(config, provider):
        _save(config, _keys(config), {**_active(config), provider: name})


def name_problem(config, provider: str, name: str) -> str:
    """Why a new key name can't be used, or "" if it's fine."""
    name = name.strip()
    if not name:
        return "Give the key a name, like Work or School."
    if len(name) > MAX_NAME_LENGTH:
        return f"Keep the name under {MAX_NAME_LENGTH} characters."
    if name.lower() in (existing.lower() for existing in names(config, provider)):
        return f"There's already a {provider} key called {name}."
    return ""


def add_key(config, provider: str, name: str, value: str = "") -> str:
    """Add a named key and make it active. Returns an error message, or "" on success."""
    problem = name_problem(config, provider, name)
    if problem:
        return problem
    name = name.strip()
    keys = _keys(config)
    provider_keys = {PRIMARY: "", **keys.get(provider, {}), name: value}
    _save(config, {**keys, provider: provider_keys}, {**_active(config), provider: name})
    return ""


def remove_key(config, provider: str, name: str) -> None:
    """Delete a named key (the Primary key can't be removed) and switch back to Primary."""
    if name == PRIMARY:
        return
    keys = _keys(config)
    provider_keys = {k: v for k, v in keys.get(provider, {}).items() if k != name}
    active = dict(_active(config))
    if active.get(provider) == name:
        active[provider] = PRIMARY
    _save(config, {**keys, provider: provider_keys}, active)


def sync_current(config) -> None:
    """Refresh the mirrored api.api_key after the provider changes."""
    _save(config, _keys(config), _active(config))
