# Visual Identity & Design System

## 1. Identity & Scope

The GitHub profile is a personal space for **technology, experimentation, hands-on learning, and automation**. The author's Public Administration career is background context, not the profile's central theme.

The existing hero artwork is intentionally preserved unchanged. Its original Public Administration-centered wording reflects a prior visual concept; future artwork changes require a separate explicit decision. Editorial copy must not repeat or amplify that older professional positioning.

## 2. Visual Principles

- Minimal, clean, readable, and professional.
- GitHub-native light and dark compatibility.
- Technology icons grouped under the existing **Core Technical Stack** headings.
- The contribution and streak analytics card is the single live generated visualization.
- Decorative visuals must never masquerade as proof of expertise or professional accomplishments.

## 3. Color Tokens

| Role | Light | Dark |
|---|---|---|
| Canvas | `#FFFFFF` / `#F6F8FA` | `#0D1117` / `#161B22` |
| Card border | `#D0D7DE` | `#30363D` |
| Divider / inactive | `#EAEEF2` | `#21262D` |
| Primary text | `#1F2328` | `#F0F6FC` |
| Secondary text | `#57606A` | `#8C959F` |
| Blue | `#0969DA` | `#58A6FF` |
| Cyan | `#218BFF` | `#79C0FF` |
| Violet | `#8250DF` | `#A371F7` |
| Green / activity | `#1A7F37` | `#3FB950` |
| Orange / streak | `#D97706` | `#FB8C00` |

Colors are implementation tokens; do not assume each accent represents a particular professional role.

## 4. Active Components

### Hero (`assets/hero-light.svg`, `assets/hero-dark.svg`)

- Original SVGs and their animation are preserved without edits.
- The README uses `<picture>` with dark/light sources and a static fallback.
- Preserve current dimensions and composition; any textual redesign of the hero is a separate scoped task.

### Contribution Streak Analytics (`streak.light.svg`, `streak.dark.svg`)

- ViewBox: 850 × 195; restrained GitHub-compatible card.
- Four zones: contributions in the last 365 days, current daily streak, longest streak, and a 35-day activity chart.
- Display metrics and chart labels in **English**, including on the Portuguese README.
- Highlight active streak dates by actual date membership; use orange for the current streak and green for other contributing days.
- Generated output is published to the `output` branch, not committed daily to `main`.

### Technical Stack Icons

- Retain the current technical stack categories and 38 × 38 icon convention.
- Hermes uses the recognizable official black-and-white `nous-girl` image instead of a synthetic lettermark.
- Icons indicate tools encountered in projects and experiments; they are not skill-level certifications.

## 5. Typography & Accessibility

Preferred system font stack:

```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
```

- Streak metrics: strong hierarchy; dates and captions remain legible at narrow widths.
- SVG `<title>`, `<desc>`, and README `alt` attributes must describe the image meaningfully.
- Text remains visible if CSS animation or SMIL motion is disabled.
- Prefer reduced-motion-compatible behavior and readable static fallbacks.
- Avoid unnecessary animation, fragile external fonts, and misleading visual indicators.
