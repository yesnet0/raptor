"""Render raptor-emitted markdown (reports, hypotheses) to HTML.

Raptor's markdown artifacts (validation-report.md, forensic-report.md,
hypothesis-*.md, root-cause-hypothesis-*.md) are produced by raptor's
LLM agents. They contain headings, fenced code blocks, tables, bullet
lists, and inline links — rendering them as raw ``<pre>`` loses all
of that structure.

Security posture: reports can include repo-, model-, and vendor-controlled
text. Raw HTML is escaped, and generated links/images are restricted to
safe URL schemes before templates render the returned HTML with ``|safe``.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

import markdown as md
from markdown.extensions import Extension
from markdown.treeprocessors import Treeprocessor

_EXTENSIONS = [
    "tables",
    "fenced_code",
    "sane_lists",
]
_SAFE_URL_SCHEMES = frozenset({"", "http", "https", "mailto"})


def _safe_url(value: str, *, allow_data_image: bool = False) -> bool:
    parsed = urlparse((value or "").strip())
    scheme = parsed.scheme.lower()
    if allow_data_image and scheme == "data":
        return parsed.path.lower().startswith("image/")
    return scheme in _SAFE_URL_SCHEMES


class _SafeLinkTreeprocessor(Treeprocessor):
    def run(self, root):
        for el in root.iter():
            tag = el.tag.rsplit("}", 1)[-1].lower()
            if tag == "a":
                href = el.get("href", "")
                if not _safe_url(href):
                    el.attrib.pop("href", None)
                    continue
                el.set("rel", "noopener noreferrer")
            elif tag == "img":
                src = el.get("src", "")
                if not _safe_url(src, allow_data_image=True):
                    el.attrib.pop("src", None)
        return root


class _SafeLinkExtension(Extension):
    def extendMarkdown(self, markdown):
        markdown.treeprocessors.register(_SafeLinkTreeprocessor(markdown), "safe_links", 15)


@lru_cache(maxsize=1)
def _converter() -> md.Markdown:
    """Reused Markdown instance (extensions are expensive to set up)."""
    converter = md.Markdown(
        extensions=[*_EXTENSIONS, _SafeLinkExtension()],
        output_format="html",
    )
    # Disable raw HTML pass-through while preserving normal Markdown escaping
    # inside inline and fenced code.
    for registry, name in (
        (converter.preprocessors, "html_block"),
        (converter.inlinePatterns, "html"),
        (converter.inlinePatterns, "entity"),
    ):
        try:
            registry.deregister(name)
        except ValueError:
            pass
    return converter


def render(text: Optional[str]) -> str:
    """Return the markdown source rendered to HTML. Empty input → ``""``."""
    if not text:
        return ""
    converter = _converter()
    try:
        html = converter.convert(text)
    finally:
        # Markdown instances are stateful across conversions — reset so
        # the next call gets a clean footnote counter etc.
        converter.reset()
    return html
