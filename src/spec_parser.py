from pathlib import Path
from typing import Dict, Any, Set, Optional
import json
import logging

from bs4 import BeautifulSoup

from util import dictify_namedtuples, make_serializable
from parsers import (
    parse_index_elements,
    parse_index_categories,
    parse_index_attributes,
    parse_index_event_handlers,
    parse_input_type_keywords,
    parse_aria_roles,
    parse_element_types,
)
from models import t_attribute


class SpecParser:
    """Encapsulates parsing, caching, and validation for HTML spec sections."""

    def __init__(
        self,
        spec_dir: Path,
        cache_dir: Path,
        global_attrs_file: Path,
        meta: Optional[Dict[str, Any]] = None,
    ):
        self.spec_dir = spec_dir
        self.cache_dir = cache_dir
        self.global_attrs_file = global_attrs_file
        self.meta = meta or {}
        self._soups: Dict[str, BeautifulSoup] = {}
        self._global_attributes: Optional[Set[str]] = None

    # ---- internal helpers ----

    def _load_soup(self, name: str) -> BeautifulSoup:
        """Lazy-load a spec file and cache the BeautifulSoup object."""
        if name not in self._soups:
            path = self.spec_dir / f"{name}.html"
            with path.open("r") as fp:
                self._soups[name] = BeautifulSoup(fp, "lxml")
        return self._soups[name]

    def _save_cache(self, key: str, data: Any) -> None:
        """Save a Python object to the cache directory as JSON."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        serialized = make_serializable(data)
        (self.cache_dir / f"{key}.json").write_text(
            json.dumps(serialized, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )

    def _load_cache(self, key: str) -> Optional[Any]:
        """Load a Python object from the cache directory; return None if missing."""
        path = self.cache_dir / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # ---- public parsers ----

    def get_global_attributes(self) -> Set[str]:
        """Parse or load cached global attributes."""
        if self._global_attributes is not None:
            return self._global_attributes

        default = {"class", "id", "role", "slot"}
        try:
            soup = self._load_soup("dom")
            anchors = (
                soup.find("h4", {"id": "global-attributes"})
                .find_next("ul", {"class": "brief"})
                .find_all("a")
            )
            parsed = default.union({a.get_text().strip() for a in anchors})
            # persist to dedicated file
            self.global_attrs_file.parent.mkdir(parents=True, exist_ok=True)
            with self.global_attrs_file.open("w", encoding="utf-8") as f:
                json.dump(sorted(parsed), f)
            self._global_attributes = parsed
            return parsed
        except Exception:
            logging.error("Could not parse global attributes from spec. Trying fallback.")
            try:
                with self.global_attrs_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._global_attributes = set(data)
                    return self._global_attributes
            except (FileNotFoundError, json.JSONDecodeError):
                logging.error("No valid fallback found. Using default set.")
                self._global_attributes = default
                return default

    def parse_elements(self) -> Dict[str, Any]:
        """Parse elements with caching and validation."""
        key = "elements"
        try:
            soup = self._load_soup("indices")
            global_attrs = self.get_global_attributes()
            raw = list(parse_index_elements(soup, global_attrs))
            if len(raw) < 50:
                raise ValueError(f"Expected >=50 elements, got {len(raw)}")
            result = dictify_namedtuples(raw, meta=self.meta)
            self._save_cache(key, result)
            logging.info(f"✅ Parsed and cached {len(raw)} elements")
            return result
        except Exception as e:
            logging.error(f"Failed to parse elements: {e}")
            cached = self._load_cache(key)
            if cached is None:
                raise RuntimeError("No cache available for elements") from e
            logging.info("📦 Loaded elements from cache")
            return cached

    def parse_categories(self) -> Dict[str, Any]:
        """Parse categories with caching and validation."""
        key = "categories"
        try:
            soup = self._load_soup("indices")
            raw = list(parse_index_categories(soup))
            if len(raw) < 5:
                raise ValueError(f"Expected >=5 categories, got {len(raw)}")
            result = dictify_namedtuples(raw, meta=self.meta)
            self._save_cache(key, result)
            logging.info(f"✅ Parsed and cached {len(raw)} categories")
            return result
        except Exception as e:
            logging.error(f"Failed to parse categories: {e}")
            cached = self._load_cache(key)
            if cached is None:
                raise RuntimeError("No cache available for categories") from e
            logging.info("📦 Loaded categories from cache")
            return cached

    def parse_attributes(self) -> Dict[str, Any]:
        """Parse attributes (including type & role) with caching and validation."""
        key = "attributes"
        try:
            indices_soup = self._load_soup("indices")
            raw = list(parse_index_attributes(indices_soup))

            # Append "type" from input.html
            input_soup = self._load_soup("input")
            raw.append(
                t_attribute(
                    name="type",
                    tag_scope={"input"},
                    description="Type of form control",
                    value_type='An input type e.g. "text"',
                    value_keywords=set(parse_input_type_keywords(input_soup)),
                    value_type_description="Type of form control",
                    separator="",
                )
            )

            # Append "role" from aria.html
            aria_soup = self._load_soup("aria")
            raw.append(
                t_attribute(
                    name="role",
                    tag_scope={"HTML"},
                    description="ARIA semantic role",
                    value_type="A concrete ARIA role",
                    value_keywords=set(parse_aria_roles(aria_soup)),
                    value_type_description="ARIA semantic role",
                    separator="",
                )
            )

            if len(raw) < 50:
                raise ValueError(f"Expected >=50 attributes, got {len(raw)}")
            # Note: merge=False for attributes
            result = dictify_namedtuples(raw, merge=False, meta=self.meta)
            self._save_cache(key, result)
            logging.info(f"✅ Parsed and cached {len(raw)} attributes")
            return result
        except Exception as e:
            logging.error(f"Failed to parse attributes: {e}")
            cached = self._load_cache(key)
            if cached is None:
                raise RuntimeError("No cache available for attributes") from e
            logging.info("📦 Loaded attributes from cache")
            return cached

    def parse_event_handlers(self) -> Dict[str, Any]:
        """Parse event handlers with caching and validation."""
        key = "event-handlers"
        try:
            soup = self._load_soup("indices")
            raw = list(parse_index_event_handlers(soup))
            if len(raw) < 50:
                raise ValueError(f"Expected >=50 event handlers, got {len(raw)}")
            result = dictify_namedtuples(raw, meta=self.meta)
            self._save_cache(key, result)
            logging.info(f"✅ Parsed and cached {len(raw)} event handlers")
            return result
        except Exception as e:
            logging.error(f"Failed to parse event handlers: {e}")
            cached = self._load_cache(key)
            if cached is None:
                raise RuntimeError("No cache available for event handlers") from e
            logging.info("📦 Loaded event handlers from cache")
            return cached

    def parse_element_types(self) -> Dict[str, Any]:
        """Parse element types with caching and validation."""
        key = "element-types"
        try:
            soup = self._load_soup("syntax")
            raw = parse_element_types(soup)
            if len(raw) < 4:
                raise ValueError(f"Expected >=4 element types, got {len(raw)}")
            # raw is already a dict; add meta
            raw["__META__"] = self.meta
            self._save_cache(key, raw)
            logging.info(f"✅ Parsed and cached {len(raw)} element types")
            return raw
        except Exception as e:
            logging.error(f"Failed to parse element types: {e}")
            cached = self._load_cache(key)
            if cached is None:
                raise RuntimeError("No cache available for element types") from e
            logging.info("📦 Loaded element types from cache")
            return cached

    def parse_all(self) -> Dict[str, Any]:
        """Convenience method to run all parsers and return a dict of results."""
        return {
            "elements": self.parse_elements(),
            "categories": self.parse_categories(),
            "attributes": self.parse_attributes(),
            "event-handlers": self.parse_event_handlers(),
            "element-types": self.parse_element_types(),
        }