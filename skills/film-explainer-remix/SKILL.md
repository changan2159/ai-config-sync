---
name: film-explainer-remix
description: Create, diagnose, or improve Chinese film-explainer videos through research-led scriptwriting and narration-driven editing. Use when the user asks for 影视解说, 主角视角解说, 电影/电视剧爆款解说, 剧情框架调研, 抖音/B站/YouTube竞品拆解, 二创文案, 字幕分镜, AI旁白, edge-tts配音, ffmpeg合成, 竖屏解说版, or complains that an explainer is chaotic, mismatched, boring, like a plot summary, or worse than mature short-video examples. Supports web/source research, benchmark deconstruction, original script rewriting, subtitle timing, voice-first audio, shot-level edit planning, external素材 planning, preview rendering, and reusable prompt/skill optimization.
---

# Film Explainer Remix

## Core Standard

Make a viewer-retention explainer, not a compressed plot recap.

The finished piece must have:
- one protagonist spine
- one active problem per beat
- researched source truth before claims
- benchmark structure analysis before style imitation
- a hook before exposition
- a new question, reversal, decision, or cost every 15-25 seconds
- visual proof for every plot claim, preferably with source timecode
- multi-shot editing for important narration lines
- narration-led audio with original sound used as texture
- intentional source-audio bridges for iconic lines, screams, reveals, impacts, or emotional holds
- readable publishing subtitles that do not fight source hard subtitles
- subtitle timing based on measured narration audio, not only planned shot duration
- shots chosen to serve narration, not source chronology
- a short pilot pass when quality, pacing, or sync is uncertain

## Operating Rule

Default to this order:

1. Research the film/series and source truth.
2. Research and deconstruct reference explainers.
3. Write an original remixed narration script.
4. Convert the script into a timed subtitle + shot-intent table.
5. Generate narration audio and measure timing.
6. Match visuals to the subtitle/audio plan at shot level.
7. Render a pilot, inspect sync/retention, then expand.

Do not start by mechanically cutting source footage. If the user provides only a video file and no title, infer enough from frames/subtitles to ask for or identify the title before committing to a full script.

## Default Decisions

- If the user asks to make a video, render a preview by default.
- If no target duration is specified, ask or choose based on platform: 3-5 minutes for short-video trial, 8-12 minutes for medium recap, 15-20 minutes for long-form film解说.
- If quality, sync, pacing, or "爆款感" is the main concern, first produce a research brief + 60-90 second style pilot plan before rendering the full video.
- If the user provides a film/series title, browse/search current web sources for plot summaries, episode guides, ending analysis, and public reference explainers unless the user explicitly says not to.
- If the user provides reference videos, analyze them before writing. Do not imitate blindly; extract reusable pacing, structure, packaging, and retention devices.
- If no reference is provided, use the default mature Chinese film-explainer pattern in `references/retention-map.md`.
- If using non-source footage, label it as `external素材`; never use it as evidence for plot facts.
- If a platform page cannot be accessed, state the limitation and use reachable sources, user-supplied links, screenshots, transcripts, or titles.

## Workflow

1. Build the research brief
   - Read `references/research-to-script-workflow.md` before planning a serious explainer.
   - Search for the film/series title, original title, release year, director/platform, plot summary, ending explanation, cast/character names, and episode/act structure.
   - Prefer primary or stable sources for facts: official synopsis, reputable databases, full plot summaries, episode recaps, subtitles/transcripts, and the user's source video.
   - Separate `confirmed facts`, `interpretations`, `popular talking points`, and `open questions`.
   - Do not invent motives, rules, chronology, or endings.

2. Benchmark winning explainers
   - Search or inspect user-provided Douyin/Bilibili/YouTube references when requested.
   - Extract structure, not wording: first sentence mechanism, hook promise, reversal cadence, shot density, subtitle style, BGM/SFX approach, cliffhanger/ending pattern.
   - Never merge, paraphrase line-by-line, or reconstruct competitor scripts. Use them as a style/structure benchmark only.
   - Summarize benchmark findings into constraints for the new version.

3. Choose the narrative strategy
   - Pick one protagonist spine and one central question.
   - Decide whether the best order is chronological, reverse hook, mid-crisis opening, ending-first mystery, or thematic clue chain.
   - Keep only details that serve hook, escalation, reversal, final choice, or payoff.
   - Convert lore into pressure: deadline, rule, risk, betrayal, body cost, moral cost.

4. Write original narration
   - Write spoken Chinese for the target duration and platform.
   - Use benchmark structures only as scaffolding; all wording, analogies, transitions, and emphasis must be original.
   - Use short clauses, active verbs, and concrete stakes.
   - Make the protagonist do something: sees, hides, tests, refuses, discovers, chooses, pays.
   - Avoid generic connectors such as `故事开始`, `然后`, `接着`, `危机来临`.
   - Do not copy original dialogue; rewrite as narration.
   - Do not narrate over every second. Mark source-audio bridge beats where the original performance carries more force than explanation.

5. Build subtitle-first timing and shot intent
   - Before rendering audio/video, create a timed table with:
     `edit_time`, `narration/subtitle`, `duration`, `emotion`, `viewer_question`, `visual_need`, `source_candidate`, `edit_method`, `audio_note`.
   - Plan how each subtitle connects to the next: suspense, answer, reversal, escalation, emotional hold, or rhythm reset.
   - Important narration beats should specify 2-5 shots: face, object, warning UI, action, consequence.
   - Shots do not need to follow movie chronology. They must match the narration's meaning and emotional job.
   - External素材 may be used for mood, transition, metaphor, map/context, internet/public background, or rhythm reset; it must not pretend to be source-plot evidence.

6. Generate and align audio
   - Read `references/voice-direction.md` when using edge-tts or AI voice.
   - Generate TTS from beat-separated lines by default; do not feed one giant paragraph unless testing a rough voice.
   - Measure generated audio durations and adjust subtitles/pauses to match real timing.
   - Preserve intentional pauses for reveals, jokes, emotional drops, and source-audio bridge moments.

7. Edit visuals to serve narration
   - Inspect with `ffprobe`.
   - Extract contact sheets and keyframes for global structure.
   - Transcribe/OCR enough dialogue and on-screen text to understand causality.
   - Build or refine a timecode index around the script's visual needs.
   - Choose footage for proof, reaction, pressure, action, consequence, bridge, and emotional hold.
   - Keep most shots 0.6-3.0 seconds unless the shot is an intentional emotional hold.

8. Package audio and visuals
   - Read `references/packaging-recipes.md` when rendering or polishing.
   - Duck original audio under narration; raise only useful alarms, impacts, doors, breaths, or one-line reactions.
   - For source-audio bridge beats, mute narration, lift original audio, and optionally keep only short source dialogue/effect subtitles.
   - Add subtitle styling that covers or avoids source hard subtitles.

9. Render, inspect, iterate
   - Use `scripts/make_edge_tts_preview.py` for edge-tts + ffmpeg previews.
   - Review the generated `*_sync_report.json`; rewrite or split beats flagged as too long or too short before judging the edit.
   - Watch the first 30 seconds as a retention test, not a plot-continuity test.
   - Fix hook, shot density, audio clarity, or subtitle readability before expanding duration.

## Reference Routing

- Use `references/research-to-script-workflow.md` for the full research -> benchmark -> original script -> timed subtitle -> audio -> edit workflow.
- Use `references/benchmark-analysis.md` when the user compares with other explainer videos or provides examples.
- Use `references/retention-map.md` for hook/beat structure and anti-chronology writing.
- Use `references/packaging-recipes.md` for editing devices, transitions, subtitles, SFX, BGM, and external素材 rules.
- Use `references/voice-direction.md` for edge-tts voice choices, segmented delivery, and mix targets.
- Use `references/vertical-output.md` for Douyin/Kuaishou/TikTok/Reels-style 9:16 output.
- Use `references/templates.md` for prompt, beat table, shot JSON, SRT, and delivery formats.
- Use `references/checklist.md` before finalizing any script, shot plan, or rendered video.

## Hard Rejections

Do not accept an output if:
- the first beat starts with worldbuilding instead of danger, contradiction, or curiosity
- competitor copy is used as rewritten text instead of structural reference
- the script was written before source truth and benchmark constraints were established for a serious film/series explainer
- the script can be summarized as `他去了A，又去了B，最后去了C`
- most shots are long unedited source intervals
- narration claims a truth without showing the clue, reaction, object, or result
- shots follow source chronology even when they fail to support the current narration
- original dialogue competes with narration
- subtitles are timed from planned clip lengths while narration audio uses different durations
- subtitles are dense, low contrast, or overlap source hard subtitles
- external素材 makes the viewer believe a non-source event happened
- the ending has no choice, cost, or emotional/thematic closure

## Deliverables

For planning tasks, output:
- research brief with source links/notes when web research was used
- benchmark deconstruction table when reference videos or platforms were analyzed
- narration script or SRT
- timed subtitle + shot-intent table
- shot table with source/external timecodes and visual reasons
- FFmpeg concat or beat JSON
- quality diagnosis and remaining risks

For rendering tasks, output:
- clickable preview video
- narration text
- SRT/ASS subtitles
- shot or beat JSON
- sync report
- filter/script files used to render
