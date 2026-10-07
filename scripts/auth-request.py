#!/usr/bin/env python3
"""Read local Polkit policy metadata; never handle credentials or execute programs."""
import json
import os
from pathlib import Path
import re
import shlex
import sys
import xml.etree.ElementTree as ET


def describe(action_id, message):
    result = {"policy": "", "name": "", "caption": "", "icon": "", "program": ""}
    language = (os.environ.get("LC_MESSAGES") or os.environ.get("LANG", "en")).split(".")[0]
    languages = [language, language.split("_")[0], None]

    def translated(node, tag):
        for language in languages:
            for child in node.findall(tag):
                if child.get("{http://www.w3.org/XML/1998/namespace}lang") == language:
                    return (child.text or "").strip()
        return ""

    for directory in ["/usr/local/share/polkit-1/actions", "/usr/share/polkit-1/actions"]:
        paths = sorted(Path(directory).glob("*.policy"), key=lambda p: (not (action_id == p.stem or action_id.startswith(p.stem + ".")), str(p)))
        for path in paths:
            try:
                policy = ET.parse(path).getroot()
            except (OSError, ET.ParseError):
                continue
            action = next((a for a in policy.findall("action") if a.get("id") == action_id), None)
            if action is None:
                continue
            annotations = {a.get("key"): a.text or "" for a in action.findall("annotate")}
            vendor = policy.findtext("vendor", "").strip()
            result.update(policy=path.stem,
                          name=vendor if vendor and not vendor.lower().startswith("the ") else path.stem.rsplit(".", 1)[-1],
                          caption=translated(action, "description"),
                          icon=action.findtext("icon_name") or policy.findtext("icon_name", ""),
                          program=annotations.get("org.freedesktop.policykit.exec.path", ""))
            break
        if result["policy"]:
            break
    if action_id == "org.freedesktop.policykit.exec" and not result["program"]:
        # pkexec's supplied message names the executable. Other requests may name
        # a document, so never infer a requesting program from their message paths.
        match = re.search(r"['\"‘’](/[^'\"‘’\r\n]+)['\"‘’]", message)
        if match:
            try:
                candidate = match[1]
                program = candidate if Path(candidate).is_file() else shlex.split(candidate)[0]
                if program.startswith("/"):
                    result["program"] = program
            except (ValueError, IndexError):
                pass
        result["name"] = Path(result["program"]).name if result["program"] else ""
    return result


if __name__ == "__main__":
    print(json.dumps(describe(sys.argv[1][:256], sys.argv[2][:8192]), ensure_ascii=False))
