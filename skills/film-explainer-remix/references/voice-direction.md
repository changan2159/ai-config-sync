# Voice Direction

Use when generating AI narration or diagnosing voice quality.

## Delivery

- Use shorter lines instead of one long paragraph.
- Segment narration by beat so pacing can change at hooks, reveals, and closures.
- Hook: faster, tense, no warm-up.
- Explanation: stable pace, lower intensity.
- Reversal: short line, slight pause, impact sound or silence.
- Ending: slower and cleaner.

## Edge TTS Defaults

Good starting points:
- male suspense/explainer: `zh-CN-YunxiNeural`, rate `+8%` to `+15%`
- female calm/suspense: `zh-CN-XiaoxiaoNeural`, rate `+5%` to `+12%`
- news-like clarity: `zh-CN-YunyangNeural`, rate `+6%` to `+12%`

Adjust:
- if it sounds sleepy, increase rate or split lines
- if it sounds mechanical, add punctuation and shorter clauses
- if consonants blur, lower BGM and source audio before changing voice

## Mix Targets

- Narration should sit clearly above everything.
- Source dialogue should usually be removed or ducked under narration.
- Preserve source sound only when it helps the story: alarm, explosion, door, breath, scream, one-line reaction.
- Avoid two intelligible voices at once.

## Practical Fixes

- Generate TTS from beat-separated text, not one giant paragraph.
- Time subtitles from measured TTS segment durations, not from the planned source-shot durations.
- If a line is more than 35% longer than its planned visual beat, split or rewrite it before adding more footage.
- If a line is more than 30% shorter than its planned visual beat, shorten the hold, add a second sentence, or use a deliberate silence/impact beat.
- Leave 0.2-0.6 seconds of visual/audio room after major reveal lines.
- Use punctuation for performance: comma for short pressure, period for finality, ellipsis only if the pause is intentional.
- If edge-tts is not expressive enough, still use it for timing pilots, then replace with a better voice for final polish.
