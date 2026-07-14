from util import make_serializable
from bs4 import BeautifulSoup
from email.utils import parsedate_to_datetime
from datetime import datetime
import logging
import json
import yaml

from constants import HTML_STEMS, ARIA_STEM
import config
from spec_parser import SpecParser


logging.basicConfig(level=config.LOG_LEVEL, format="%(levelname)s: %(message)s")


def read_timestamp(path: Path) -> tuple[str, datetime]:
    raw = path.read_text().strip()
    return raw, parsedate_to_datetime(raw)


# Read NOTICE and update with timestamps
NOTICE = config.NOTICE_FILE.read_text().split("\n\n")

whatwg_times = [
    read_timestamp(config.SPEC_DIR / f"{stem}.time")
    for stem in HTML_STEMS
]
whatwg_time = max(whatwg_times, key=lambda pair: pair[1])[0]
aria_time = read_timestamp(config.SPEC_DIR / f"{ARIA_STEM}.time")[0]

updates = {
    "The HTML Living Standard": whatwg_time,
    "Accessible Rich Internet Applications (WAI-ARIA)": aria_time,
}

for prefix, published in updates.items():
    for i, paragraph in enumerate(NOTICE):
        if paragraph.startswith(prefix):
            NOTICE[i] = f"{paragraph} (as last published at {published})"
            break
    else:
        raise ValueError(f"licenses/NOTICE: no paragraph found starting with {prefix!r}")

NOTICE = [x.replace("\n", " ").strip() for x in NOTICE]
META = {"copyright": NOTICE}


def write_output(data: dict, path: Path, fmt: str) -> None:
    """Write data to path in the specified format (json or yaml)."""
    serializable = make_serializable(data)
    if fmt == "json":
        path.write_text(
            json.dumps(serializable, indent=4, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
    elif fmt == "yaml":
        path.write_text(
            yaml.dump(serializable, indent=2, sort_keys=True, allow_unicode=True),
            encoding="utf-8",
        )
    else:
        raise ValueError(f"Unsupported output format: {fmt}")


def main():
    # Prepare output directory
    config.JSON_DIR.mkdir(parents=True, exist_ok=True)

    # Instantiate the parser
    parser = SpecParser(
        spec_dir=config.SPEC_DIR,
        cache_dir=config.CACHE_DIR,
        global_attrs_file=config.GLOBAL_ATTRS_FILE,
        meta=META,
    )

    # Parse everything
    results = parser.parse_all()

    # Determine file extension
    ext = "json" if config.OUTPUT_FORMAT == "json" else "yaml"

    # Write each result
    for name, data in results.items():
        output_path = config.JSON_DIR / f"{name}.{ext}"
        write_output(data, output_path, config.OUTPUT_FORMAT)
        logging.info(f"📝 Wrote {output_path}")


if __name__ == "__main__":
    main()
