"""Refresh src/page_blocks/ from Scanova's own sources.

The page tools build landing pages in the page builder's block format. The
format is owned by two repos, so this copies it here rather than restating it:

- qcg-backend  src/qr_manager/json_schema/{v2,categories/components}: the JSON
  Schemas a page's blocks must pass to publish (copied as-is to schemas/).
- qcg-frontend-next  packages/blocks/src/blocks/landing/*/definition.ts: each
  block's label, limit, categories, fields and defaults (dumped to blocks.json
  by dump_block_definitions.mjs, which needs `npm i esbuild` next to it).

Usage: python scripts/sync_page_blocks.py <qcg-backend checkout> <qcg-frontend-next checkout>
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "src" / "page_blocks"

# Blocks an assistant shouldn't place on an ordinary page: they belong to a
# special page type (intro/document/image pages, cover/main pages), only make
# sense on a GS1 code, or run the customer's own JavaScript.
LEFT_OUT = {
    "auto_redirect", "document_viewer", "image_gallery", "cover_page", "main_page", "intro_page",
    "gs1_info", "custom_script",
}


def main(backend: Path, frontend: Path) -> None:
    src = backend / "src" / "qr_manager" / "json_schema"
    schemas = OUT / "schemas"
    if schemas.exists():
        shutil.rmtree(schemas)
    shutil.copytree(src / "v2", schemas / "v2")
    shutil.copytree(src / "categories" / "components", schemas / "categories" / "components")
    shutil.copytree(backend / "src" / "theme_manager" / "json_schema", schemas / "theme")

    dumped = json.loads(subprocess.run(
        ["node", str(HERE / "dump_block_definitions.mjs"), str(frontend)],
        check=True, capture_output=True, text=True,
    ).stdout)
    allowed = json.loads((src / "v2" / "page-types" / "component-page.json").read_text())
    allowed = allowed["items"]["allOf"][1]["properties"]["type"]["enum"]
    blocks = {}
    for block_type in allowed:
        d = dumped.get(block_type)
        if block_type in LEFT_OUT or not d or "error" in d:
            continue
        blocks[block_type] = {
            "label": d.get("label"),
            "description": d.get("description"),
            "limit": d.get("limit"),
            "removable": d.get("canDelete") is not False,
            "categories": d.get("allowedInCategories"),
            "fields": d.get("fields") or [],
            "defaults": d.get("defaults") or {},
        }
    (OUT / "blocks.json").write_text(json.dumps(blocks, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(blocks)} blocks, schemas from {src}")


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]))
