# Built-in checks

| Rule | Purpose | WCAG mapping |
|---|---|---|
| `page-lang` | Missing document language | 3.1.1 |
| `page-title` | Missing/empty title | 2.4.2 |
| `heading-h1` | No level-one heading | 1.3.1, 2.4.6 |
| `image-alt` | Image lacks alt attribute | 1.1.1 |
| `form-label` | Form control lacks accessible name | 3.3.2, 4.1.2 |
| `link-name` | Link/button lacks accessible name | 2.4.4, 4.1.2 |
| `link-purpose` | Generic link text | 2.4.4 |
| `main-landmark` | Missing main landmark | 1.3.1 |
| `target-size` | Interactive target below 24x24 CSS px | 2.5.8 |

If local `axe.min.js` is installed, axe-core checks are added. Automated checks cannot detect every accessibility barrier and do not establish WCAG conformance.
