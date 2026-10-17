# Visual Identity & Design System

## 1. Positioning & Philosophy

**Tecnologia e Inovação na Administração Pública**  
**Automação · Dados · IA Agêntica**

The visual identity is anchored in the understanding of public-sector administrative processes, visually demonstrating how rules, institutional context, and data are transformed into operational capability and applied digital solutions. Legal training provides the foundation for systemic rules analysis. Tools, libraries, and AI models serve as instruments rather than core identity elements.

---

## 2. Concept: The Synaptic Public System

The visual signature marries the organic responsiveness of a neural synapse with the rigor of an administrative process pipeline. Four operational nuclei define the transformation journey:

1. **Public Context**: Legal frameworks, compliance, and real-world administrative workflows.
2. **Data**: Structured information, APIs, and canonical registries.
3. **Applied & Agentic AI**: Deterministic workflows, agentic orchestration, and systems integration.
4. **Digital Solutions**: Delivered capabilities, automated operations, and concrete practical improvement.

Parallel visual conduits reflect the non-linear realities of institutional processes. Signals propagate from left to right in phased pulses across primary and auxiliary routes. The four functional colors—Blue, Cyan, Violet, and Green—represent progression through these stages without decorative noise.

---

## 3. Unified Design Tokens & Palette

### 3.1 Global Chromatic System

| Role | Light Theme | Dark Theme | Functional Meaning |
|---|---|---|---|
| **Canvas Background** | `#FFFFFF` → `#F6F8FA` | `#0D1117` → `#161B22` | GitHub-native neutral environment |
| **Card Border** | `#D0D7DE` | `#30363D` | Structural delineation and grid borders |
| **Divider / Inactive** | `#EAEEF2` | `#21262D` | Internal column dividers, inactive calendar cells |
| **Text Primary** | `#1F2328` | `#F0F6FC` | Headline metrics, titles, values |
| **Text Secondary** | `#57606A` | `#8C959F` | Section labels, subtitles, axis text |
| **Text Muted** | `#8C959F` | `#6E7681` | Footers, telemetries, secondary dates |
| **Blue (Context)** | `#0969DA` | `#58A6FF` | Public context, longest streaks, trust |
| **Cyan (Data)** | `#218BFF` | `#79C0FF` | Information flow, data pipelines |
| **Violet (Agentic AI)** | `#8250DF` | `#A371F7` | Applied AI, automated agents, workflows |
| **Green (Solution)** | `#1A7F37` | `#3FB950` | Delivered outcomes, contribution activity bars |
| **Orange (Streak)** | `#D97706` | `#FB8C00` | Unbroken daily streak focus, flame highlight |

---

## 4. Component Visual Systems

### 4.1 Hero Header (`assets/hero-*.svg`)
- **Dimensions**: 1200 × 370 viewBox, 64px horizontal safety margins.
- **Grid Structure**: 28-unit technical grid, softened along borders.
- **Typography**: Name at 34 units; positioning at 19 units; pillars at 14 units (`AUTOMAÇÃO · DADOS · IA AGÊNTICA`).
- **Signal Motion**: Native SMIL continuous 6.4-second animation cycle with phase shifts of 0s, -1.6s, -3.2s, and -4.8s.

### 4.2 Contribution Streak Analytics (`streak.*.svg`)
- **Dimensions**: 850 × 195 viewBox, 10px rounded card borders.
- **Zone 1 (Last 365 Days)**: Prominent 28px bold count, active days telemetry, rolling year scope.
- **Zone 2 (Current Streak Centerpiece)**: 28px streak count seated inside a 39px radius halo ring with a flame glyph crown and subtle radial glow.
- **Zone 3 (Longest Streak)**: 28px record count, exact date range formatted as `MMM DD, YYYY`, historical context.
- **Zone 4 (Recent Activity)**: 35-day discrete daily volume bars. Active streak dates are highlighted in Orange based on true date membership; non-streak active days use Green; zero-activity days use a muted 3.5px baseline tick.

### 4.3 Langton's Ant Automaton (`langton-contribution-graph*.svg`)
- **Dimensions**: Matching GitHub's standard 53×7 contribution calendar geometry (11px cells, 3px gaps, 14px step pitch).
- **Automaton Behavior**: Classical binary RL rules seeded directly by contribution density ($C(d) > 0 \implies \text{state 1}$).
- **Visualization Layers**: Base GitHub calendar levels, dynamic cell inversion overlays, fading tail trail, and oriented computational agent silhouette.

### 4.4 Custom Badges (`assets/badges/*.svg`)
- **Geometry**: 256 × 256 or 64 × 64 viewBox with rounded corners.
- **Style**: Dark minimal aesthetic matching GitHub developer tooling (`codex`, `google-antigravity`, `orca-ade`, `hermes`, `n8n`, `rest-apis`, `webhooks`).

---

## 5. Typography & Font Stacks

All SVG graphics and documentation use GitHub's standard system font stack:
```css
font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans", Helvetica, Arial, sans-serif;
```
- **Headline Numbers**: 28px, font-weight 700.
- **Section Headers & Metric Labels**: 11px, font-weight 600, letter-spacing 0.5px, uppercase.
- **Date Ranges & Subtitles**: 11px, font-weight 400.
- **Chart Axes**: 10px, font-weight 400.

---

## 6. Accessibility & Motion Governance

1. **Static Readability (Zero Initial Opacity Elimination)**:
   - Text elements render at 100% opacity by default.
   - Entrance animations do not use `opacity: 0` as a default inline state, ensuring readability across static SVG proxies, mobile readers, and image previewers.
2. **Reduced Motion**:
   - Every animated SVG includes a `@media (prefers-reduced-motion: reduce)` media query that disables dynamic looping, scaling, and entrance animations.
3. **Semantic Tags**:
   - SVGs include `<title>` and `<desc>` elements providing complete textual summaries for screen readers.
4. **Color Contrast**:
   - All text-to-background combinations exceed WCAG 2.1 AA standards (minimum 4.5:1 for normal text and 3:1 for large metrics).
