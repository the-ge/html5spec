from pathlib import Path

# ---- Project root ----
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# ---- Directories ----
SPEC_DIR = PROJECT_ROOT / ".dev/state"             # raw spec HTML files
JSON_DIR = PROJECT_ROOT / "spec-json"       # final JSON output
CACHE_DIR = PROJECT_ROOT / ".dev" / "cache"        # cached parsed data
GLOBAL_ATTRS_FILE = SPEC_DIR / "global_attributes"

# ---- Licenses ----
LICENSES_DIR = PROJECT_ROOT / "licenses"
NOTICE_FILE = LICENSES_DIR / "NOTICE"

# ---- Logging ----
LOG_LEVEL = "INFO"

# ---- Output format ----
OUTPUT_FORMAT = "json"
