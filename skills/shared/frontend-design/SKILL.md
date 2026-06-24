---
name: frontend-design
description: Create and improve production-grade frontend interfaces with strong layout, spacing, hierarchy, responsive behavior, and visual quality. Use when the user asks to build, redesign, polish, beautify, or fix the look and experience of web UI, including pages, dashboards, forms, apps, landing pages, React/Vue/Svelte/HTML/CSS layouts, screenshots, or complaints that a page is ugly, cramped, too wide, uneven, wasteful, generic, or hard to use. For formal review use design-review or frontend-design-review; for component architecture and reuse pair with frontend-ui-engineering and code-maintainability.
---

This skill guides creation and optimization of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to layout, density, hierarchy, responsive behavior, and interaction quality.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Quality Bar

Treat frontend work as visual product design, not decoration. A successful result should have a clear concept, a recognizable art direction, production-ready implementation, responsive behavior, accessible interaction states, and enough crafted detail that it does not look like a default template.

For greenfield or high-visibility UI, do not start by assembling common cards, centered hero blocks, generic gradients, and stock component layouts. First define the visual thesis, then make every major choice support it.

For existing UI, do not begin by adding decoration. First audit whether the page uses space well: what deserves width, what should be compact, what is visually dominant, what is crowded, what can be grouped, and what should move into sidebars, drawers, tabs, toolbars, accordions, or denser table/list patterns.

## Workflow

1. Inspect the target app or task constraints before designing: framework, component system, styling approach, assets, accessibility expectations, and nearby UI.
2. For an existing page, run a short layout audit before editing: primary task, content priority, wasted space, cramped zones, grid/flex sizing, max-widths, responsive breakpoints, tap targets, and visual hierarchy.
3. Decide a design thesis in one sentence: audience, mood, memorable motif, and what should feel different from standard SaaS/admin/landing-page UI.
4. Choose a system: information architecture, layout grid, spacing rhythm, density level, typography scale, color story, surfaces, elevation/borders, icon/illustration treatment, motion rules, and responsive behavior.
5. Implement with existing primitives when possible, but add art direction through composition, tokens, theme, imagery, copy hierarchy, and motion.
6. Verify visually when feasible with a browser screenshot across the most important viewport sizes, then iterate on the largest visible weaknesses instead of only checking compilation.

When the user asks to "optimize", "polish", "make it prettier", "fix layout", "improve UX", or gives a screenshot, default to this sequence:

1. Identify the top 3 visible problems by impact.
2. Explain the intended layout change briefly if the task is non-trivial.
3. Edit the smallest set of components/styles that fixes those problems.
4. Re-open or screenshot the page when possible and check whether the changes actually improved spacing, hierarchy, and responsiveness.

When inspiration, pattern selection, or library choice would materially improve the result, read `references/awesome-frontend-design-map.md`. Use it as a curated map derived from the `sindresorhus/awesome` ecosystem and adjacent design resources; do not load it for small routine edits.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Existing Projects

- In an existing app, inspect the current design system, component library, tokens, layout primitives, utilities, and nearby pages before creating new UI building blocks.
- Prefer composing or extending existing components and styles when they fit; make the visual direction distinctive through arrangement, content, motion, and theme rather than parallel one-off primitives.
- Create new components or styling primitives only when reuse would fight the requested experience, accessibility, or maintainability.
- Preserve established UX conventions for critical flows. Make the interface more beautiful by sharpening hierarchy, rhythm, affordances, and brand expression rather than surprising users where predictability matters.

## Layout And UX Audit

Before editing existing frontend UI, check these issues explicitly:

- **Space budget**: Allocate width and height by user value. Dense controls, filters, metadata, and secondary actions should not consume the same space as primary content, data visualization, forms, canvases, editors, or tables.
- **Content hierarchy**: Make the primary task immediately visible. Use size, weight, position, contrast, and grouping so users can scan instead of reading every element.
- **Layout structure**: Prefer intentional grids, split panes, sidebars, sticky toolbars, tabbed regions, drawers, and responsive columns over one large undifferentiated stack of cards.
- **Density fit**: Operational tools, dashboards, admin screens, data tables, and editors usually need compact, scannable density. Marketing, editorial, and showcase pages can use more negative space, but it must still serve focus.
- **Container sizing**: Avoid full-width blocks for narrow content. Use `max-width`, intrinsic sizing, fixed tool columns, `minmax()`, `clamp()`, and stable aspect ratios so content does not sprawl or collapse.
- **Responsive behavior**: Design the mobile, tablet, and desktop arrangements intentionally. Do not merely stack everything if that hides the primary workflow or makes controls dominate the page.
- **Interaction states**: Include hover, focus, active, loading, empty, disabled, error, selected, and keyboard states when relevant.
- **Text and controls**: Text must fit in buttons, tabs, cards, sidebars, and table cells without overlap. Controls should have stable dimensions so labels, icons, and counters do not shift the layout.
- **Accessibility**: Check readable contrast, semantic structure, visible focus, keyboard reachability, reduced-motion behavior where relevant, and practical touch target size.

If a design feels spacious but the task area is cramped, reduce chrome before shrinking primary content. If everything feels equally important, lower the emphasis of secondary surfaces before increasing decoration.

## Frontend Aesthetics Guidelines

Focus on:
- **Typography**: Choose fonts that are beautiful, unique, and interesting. Avoid generic fonts like Arial and Inter; opt instead for distinctive choices that elevate the frontend's aesthetics; unexpected, characterful font choices. Pair a distinctive display font with a refined body font.
- **Color & Theme**: Commit to a cohesive aesthetic. Use CSS variables for consistency. Dominant colors with sharp accents outperform timid, evenly-distributed palettes.
- **Motion**: Use animations for effects and micro-interactions. Prioritize CSS-only solutions for HTML. Use Motion library for React when available. Focus on high-impact moments: one well-orchestrated page load with staggered reveals (animation-delay) creates more delight than scattered micro-interactions. Use scroll-triggering and hover states that surprise.
- **Spatial Composition**: Use unexpected layouts only when they improve clarity. Asymmetry, overlap, diagonal flow, and grid-breaking elements can work, but primary workflows still need predictable scanning, stable alignment, and clear space allocation.
- **Backgrounds & Visual Details**: Create atmosphere and depth rather than defaulting to solid colors. Add contextual effects and textures that match the overall aesthetic. Apply creative forms like gradient meshes, noise textures, geometric patterns, layered transparencies, dramatic shadows, decorative borders, custom cursors, and grain overlays.
- **Interaction Quality**: Design hover, focus, active, loading, empty, disabled, and error states as first-class visuals. Make keyboard focus visible and avoid motion that blocks task completion.
- **Content Hierarchy**: Improve copy hierarchy and information scent. Beautiful UI fails if all text, cards, charts, or controls compete with equal weight.

NEVER use generic AI-generated aesthetics like overused font families (Inter, Roboto, Arial, system fonts), cliched color schemes (particularly purple gradients on white backgrounds), predictable layouts and component patterns, and cookie-cutter design that lacks context-specific character.

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (Space Grotesk, for example) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

## Visual QA Gate

Before considering the frontend complete, check:
- Does the first viewport have a clear focal point and memorable visual idea?
- Are typography, color, spacing, surfaces, and motion part of one coherent system?
- Does the layout allocate space according to importance, or are low-value panels taking room from high-value content?
- Are narrow controls, filters, badges, labels, and metadata constrained instead of stretched across the page?
- Are crowded areas solved through grouping, hierarchy, progressive disclosure, or layout changes rather than smaller text alone?
- Is there at least one non-generic composition choice: asymmetric grid, editorial rhythm, custom illustration/texture, distinctive data treatment, or unconventional but usable navigation?
- Are responsive states intentionally designed rather than merely stacked?
- Are accessibility basics covered: contrast, semantic structure, keyboard focus, reduced-motion fallback where relevant, and readable tap targets?
- Did screenshots or visual inspection confirm that desktop, tablet, and mobile layouts have no obvious overlaps, clipped text, blank dead zones, or cramped primary workflows?
- Would this still look intentional if the brand name and copy were swapped out? If yes, it is too generic; add context-specific character.
