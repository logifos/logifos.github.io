#!/usr/bin/env python3
"""Check built contract references offline; optionally inspect the pinned Git tree."""

import argparse
from collections import Counter
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
REFERENCES = {
    "guide": "docs/CONTRACT.md",
    "request": "contracts/request.schema.json",
    "response": "contracts/response.schema.json",
    "payload_pins": "contracts/pins.json",
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read_metadata(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    require(data["repository"] == "https://github.com/logifos/logifos-rs", "unexpected core repository")
    require(re.fullmatch(r"[0-9a-f]{40}", data["revision"]), "core revision must be a full immutable Git SHA")
    require(data["release"] is None, "no release has been qualified; release must remain null")
    for name in ("abi_version", "schema_version"):
        require(type(data[name]) is int and data[name] > 0, f"invalid {name}")
    require(data["references"] == REFERENCES, "contract reference paths differ from the core contract layout")
    return data


class References(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.values = []
        self.capture = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if "href" in attrs:
            self.links.append((attrs["href"], attrs.get("data-contract-reference")))
        for marker in ("data-contract-version", "data-wire-example"):
            if marker in attrs:
                require(self.capture is None, "nested contract markers")
                self.capture = (tag, marker, attrs[marker], [])

    def handle_data(self, data):
        if self.capture:
            self.capture[3].append(data)

    def handle_endtag(self, tag):
        if self.capture and self.capture[0] == tag:
            _, marker, key, parts = self.capture
            self.values.append((marker, key, "".join(parts).strip()))
            self.capture = None


def check_pages(dist, data):
    expected = {
        key: f"{data['repository']}/blob/{data['revision']}/{path}"
        for key, path in REFERENCES.items()
    }
    files = sorted(dist.glob("*.html"))
    require(files, "no built HTML found; run npm run build first")
    found_pages = set()
    link_count = version_count = example_count = 0
    for path in files:
        page = References()
        page.feed(path.read_text(encoding="utf-8"))
        page.close()
        require(page.capture is None, f"{path.name}: unclosed contract marker")
        keys = Counter()
        for href, key in page.links:
            url = urlsplit(href)
            is_core = url.netloc == "github.com" and url.path.startswith("/logifos/logifos-rs/")
            is_contract = is_core and any(url.path.endswith(f"/{ref}") for ref in REFERENCES.values())
            if key is not None or is_contract:
                require(key in expected, f"{path.name}: unlabelled or unknown contract reference")
                require(href == expected[key], f"{path.name}: mutable, mismatched or malformed {key} link")
                keys[key] += 1
                link_count += 1
        versions = Counter()
        for marker, key, value in page.values:
            if marker == "data-contract-version":
                require(key in ("abi", "schema"), f"{path.name}: unknown version marker")
                require(value == str(data[f"{key}_version"]), f"{path.name}: stale {key} version")
                versions[key] += 1
                version_count += 1
            else:
                require(key == "negotiate", f"{path.name}: unknown wire example")
                require(json.loads(value) == {
                    "schema_version": data["schema_version"],
                    "abi_version": data["abi_version"],
                    "op": "negotiate",
                }, f"{path.name}: stale negotiation example")
                example_count += 1
        if path.name in ("api.html", "status.html"):
            require(keys == Counter({key: 1 for key in REFERENCES}), f"{path.name}: missing or duplicate contract links")
            require(versions == Counter(abi=1, schema=1), f"{path.name}: missing or duplicate versions")
            found_pages.add(path.name)
    require(found_pages == {"api.html", "status.html"}, "missing API or status page")
    require(example_count == 1, "expected one target negotiation example")
    return link_count, version_count


def walk(value):
    yield value
    if isinstance(value, dict):
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def git_file(checkout, revision, path):
    result = subprocess.run(
        ["git", "--no-optional-locks", "-C", str(checkout), "show", f"{revision}:{path}"],
        capture_output=True, check=False,
    )
    require(result.returncode == 0, f"pinned core file is unavailable locally: {path}")
    return result.stdout.decode("utf-8")


def check_core(checkout, data):
    sources = {key: git_file(checkout, data["revision"], path) for key, path in REFERENCES.items()}
    ref_count = 0
    for key in ("request", "response"):
        schema = json.loads(sources[key])
        for branch in schema["oneOf"]:
            for version in ("abi_version", "schema_version"):
                require(branch["properties"][version] == {"const": data[version]}, f"{key}: {version} differs from pinned core")
        for value in walk(schema):
            if not isinstance(value, dict) or "$ref" not in value:
                continue
            ref = value["$ref"]
            require(ref.startswith("#/"), f"{key}: external schema reference needs an explicit pin")
            target = schema
            for part in ref[2:].split("/"):
                part = part.replace("~1", "/").replace("~0", "~")
                require(isinstance(target, dict) and part in target, f"{key}: unresolved schema reference {ref}")
                target = target[part]
            ref_count += 1
    pins = json.loads(sources["payload_pins"])
    for name in ("formula", "mathml_syntax"):
        require(all(pins[name][key] is None for key in ("revision", "schema_path", "sha256")), f"{name}: payload pin changed; review unresolved-pin documentation")
    require("does **not** implement it" in sources["guide"], "review the documented implementation status")
    return ref_count


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--core-checkout", type=Path, help="read committed files at the pinned revision; no network or worktree writes")
    args = parser.parse_args()
    try:
        data = read_metadata(ROOT / "src/data/contract.json")
        for directory in ("src", "public", "contracts"):
            require(not list((ROOT / directory).rglob("*.schema.json")), "schemas belong in the core; remove the local copy")
        links, versions = check_pages(ROOT / "dist", data)
        print(f"PASS: {links} immutable contract links, {versions} version references, 1 target request example")
        if args.core_checkout:
            refs = check_core(args.core_checkout, data)
            print(f"PASS: 4 pinned core files, matching wire versions, {refs} internal schema references, 2 unresolved payload pins")
        else:
            print("Local consistency only; core file existence and schema references were not checked. Use --core-checkout PATH for that check.")
        print("Offline checks only; remote availability, engine behavior and release support are not verified.")
    except (ValueError, KeyError, TypeError, OSError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
