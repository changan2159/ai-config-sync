# Awesome Frontend Design Map

This is a selective, design-oriented map inspired by `sindresorhus/awesome` and related Awesome lists. Use it to sharpen inspiration, pattern choice, and library selection for frontend work. Do not treat it as a checklist or load every external resource.

## When To Use

- Use for high-visibility pages, new visual systems, landing pages, dashboards, data-heavy UI, animation-heavy UI, or when the first design direction feels generic.
- Use when choosing typography, color systems, animation approaches, CSS/SVG/Canvas/WebGL techniques, accessibility references, or design-system patterns.
- Skip for small fixes, bug repairs, routine form layout, or projects with strict existing design direction.

## Search Anchors

When live research is useful, search the relevant Awesome list or topic instead of browsing broad inspiration feeds:

- `site:github.com/sindresorhus/awesome "Front-End Development"`
- `awesome css github`
- `awesome web typography github`
- `awesome motion ui design github`
- `awesome web animation github`
- `awesome design systems github`
- `awesome accessibility github web`
- `awesome svg github`
- `awesome canvas github`
- `awesome creative coding github`
- `awesome dataviz github`
- `awesome design tools github`
- `awesome web performance github`

## Design Resource Categories

- **CSS craft**: Use for layout experiments, custom properties, masks, container queries, scroll effects, grid/subgrid, shape-outside, blend modes, and CSS-only visual effects.
- **Typography**: Use for font pairing, variable fonts, optical sizing, editorial hierarchy, internationalization constraints, and readable scales.
- **Motion and animation**: Use for page-load choreography, scroll storytelling, transitions, gesture feedback, animated data, and reduced-motion fallbacks.
- **SVG and illustration systems**: Use for icon systems, diagrammatic hero art, generative ornaments, masks, filters, duotone treatments, and responsive vector assets.
- **Canvas, WebGL, and creative coding**: Use when the memorable motif needs particles, simulation, generative backgrounds, custom charts, immersive hero effects, or tactile visual systems.
- **Accessibility**: Use for contrast, focus states, keyboard navigation, landmarks, screen-reader semantics, form errors, motion sensitivity, and touch target sizing.
- **Design systems**: Use for tokens, component anatomy, theming, density modes, documentation, state matrices, and long-term maintainability.
- **Data visualization**: Use for dashboards, analytics, maps, timelines, dense tables, comparison views, and chart interaction.
- **Performance**: Use when visual ambition risks layout shift, blocking fonts, oversized images, heavy animation, or main-thread jank.

## Practical Upgrade Patterns

- Replace generic hero sections with a concept-specific scene: editorial masthead, product schematic, tactile object, data artifact, timeline, map, instrument panel, or staged workflow.
- Replace evenly spaced cards with a deliberate composition: asymmetric grid, bento rhythm with hierarchy, split editorial layout, layered canvases, pinned side narrative, or dense command-center view.
- Replace one accent color with a color system: base atmosphere, dominant surface, quiet text range, sharp action accent, semantic states, and one memorable contrast moment.
- Replace default fonts with a pair: expressive display face for identity plus highly readable body face. Keep fallback stacks deliberate and respect language coverage.
- Replace scattered hover effects with motion rules: entrance choreography, state feedback, spatial transitions, and reduced-motion behavior.
- Replace decorative backgrounds with contextual atmosphere: texture, diagram lines, chart fragments, product materials, environmental light, brand geometry, or functional data patterns.
- Replace one-off CSS values with tokens: spacing scale, radius scale, shadows, color variables, typography scale, timing curves, and z-index layers.

## Library Choice Heuristics

- Prefer CSS and SVG for static or moderately animated visuals because they are accessible, inspectable, and cheaper than canvas/WebGL.
- Use Canvas when there are many moving elements, procedural textures, particles, dense charts, or pixel-level effects.
- Use WebGL/Three.js only when depth, lighting, shader effects, or 3D interaction materially improves the concept.
- Use motion libraries when stateful choreography would be brittle in CSS, but keep animations purposeful and interruptible.
- Use charting libraries for standard analytics, but consider custom SVG/Canvas for signature data moments that need brand expression.
- Avoid adding a dependency for a visual effect that can be achieved clearly with existing project tools.

## Visual QA Prompts

- What is the one memorable visual idea?
- Which existing design convention are we intentionally preserving for usability?
- Which convention are we breaking for distinctiveness?
- Does the typography have hierarchy, personality, and language coverage?
- Does motion explain state or create atmosphere, instead of just moving things?
- Does the interface still work with keyboard, reduced motion, narrow screens, long text, empty states, and error states?
- What would make a screenshot immediately identifiable as belonging to this product or context?
