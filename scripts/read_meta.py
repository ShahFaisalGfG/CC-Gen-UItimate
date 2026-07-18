"""Output app metadata from pyproject.toml as JSON on stdout."""
import tomllib
import json
import pathlib

_toml = pathlib.Path(__file__).parent.parent / "pyproject.toml"

with _toml.open("rb") as _fh:
    _data = tomllib.load(_fh)

_project = _data["project"]
_ccgen = _data.get("tool", {}).get("ccgen", {})

print(json.dumps({
    "Version":   _project["version"],
    "AppName":   _ccgen.get("display_name", "CC-Gen-Ultimate"),
    "Publisher": _ccgen.get("publisher", "gfgRoyal"),
    "Url":       _ccgen.get("url", ""),
    "ExeName":   _ccgen.get("exe_name", "CC-Gen-Ultimate.exe"),
    "WingetId":  _ccgen.get("winget_id", ""),
}))
