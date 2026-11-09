"""Regenerates src/companyenrich/_generated.py from openapi/v2.json.

Pass --fetch to download the latest spec from the API first.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = ROOT / "openapi" / "v2.json"
OUTPUT = ROOT / "src" / "companyenrich" / "_generated.py"
SPEC_URL = "https://api.companyenrich.com/openapi/v2.json"

# The spec describes these embedded records as arbitrary JSON. Point them at the real types.
REFINEMENTS = {
    "JsonElement": "CompanyResponse",
    "JsonElement2": "PersonResponse",
    "NullableOfJsonElement": "CompanyResponse2",
}


def main() -> None:
    if "--fetch" in sys.argv[1:]:
        with urllib.request.urlopen(SPEC_URL, timeout=60) as response:
            SPEC.write_bytes(response.read())

    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    schemas = spec["components"]["schemas"]
    for name, target in REFINEMENTS.items():
        schemas[name] = {"$ref": f"#/components/schemas/{target}"}

    with tempfile.TemporaryDirectory() as directory:
        patched = Path(directory) / "v2.json"
        patched.write_text(json.dumps(spec), encoding="utf-8")
        subprocess.run(
            [
                "datamodel-codegen",
                "--input", str(patched),
                "--input-file-type", "openapi",
                "--output", str(OUTPUT),
                "--output-model-type", "typing.TypedDict",
                "--target-python-version", "3.10",
                "--enum-field-as-literal", "all",
                "--use-union-operator",
                "--use-standard-collections",
                "--strict-nullable",
                "--disable-timestamp",
                "--formatters", "ruff-format",
            ],
            check=True,
        )  # fmt: skip


if __name__ == "__main__":
    main()
