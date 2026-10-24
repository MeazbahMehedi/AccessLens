# Rules and result interpretation

## Primary engine

The bundled axe-core 4.10.3 script evaluates the selected cumulative WCAG tags and best practices. Only WCAG-tagged failures in the chosen A/AA/AAA target affect the score. Obsolete or unrelated-standard rules are excluded. Success-criterion tags such as `wcag2411` are parsed as `2.4.11`.

One finding represents a failed rule on an affected element. Duplicate rule/target/category records are removed. axe-core incomplete results become manual-review items. Best-practice findings have no asserted WCAG level and do not reduce the score.

## Basic fallback

When axe-core cannot load or execute, the scanner checks missing document language/title, visible images with missing text alternatives, form-control names and link/button names. It resolves ARIA label references and ignores hidden/inert elements for these checks. Missing h1/main landmark recommendations are best practices. A vague “read more” link is not automatically treated as a failure without evaluating context. The fallback deliberately omits target-size and contrast assertions.

Basic coverage is limited. It is not equivalent to running axe-core and does not support an accessibility certification.

## Accuracy corrections

- Missing h1/main elements do not alone prove WCAG failure.
- WCAG 2.5.8 is AA, with spacing and other exceptions. The previous blanket size check was removed; axe-core evaluates the rule.
- Rule tags determine target level; fallback checks are essential Level A checks.
- Hidden controls and valid ARIA names no longer trigger the previous blanket custom checks.
- Best practices and incomplete results are kept out of scored findings.
- Repeated elements use a capped rule penalty. See README for the scoring formula.
- HTTP error and recognizable bot-challenge pages do not produce valid-page scores.
- Challenge and consent recognition is heuristic. Inspect the screenshot and final URL.

## Sources

- W3C WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Target Size (Minimum), including exceptions: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum
- axe-core API and tags: https://www.deque.com/axe/core-documentation/api-documentation/

Automated checking covers part of accessibility. Test keyboard, screen reader, zoom, captions, content meaning and complete user tasks manually.
