# Research To Script Workflow

Use this when producing a serious Chinese film/series explainer, especially long-form 8-20 minute videos or any task where the user wants a "爆款解说" rather than a rough automatic cut.

## Principle

The correct order is:

```text
剧情事实和竞品结构 -> 原创解说文案 -> 字幕时间轴和情绪规划 -> 配音音频 -> 按字幕反找画面 -> 粗剪/精剪/包装
```

Do not cut video first and then force narration onto it. The narration and subtitle timeline are the spine; visuals serve that spine.

## 1. Research Brief

Collect enough truth to avoid wrong plot claims.

Minimum fields:

| Field | Notes |
| --- | --- |
| Title | Chinese title, original title, year, film/series/episode scope |
| Premise | 1-2 sentence setup |
| Main characters | names, relationships, wants, secrets |
| Full plot spine | beginning, lock-in, midpoint, reversal, climax, ending |
| Rules/lore | only facts supported by source or credible summaries |
| Ending explanation | what actually happened and what remains ambiguous |
| Popular talking points | what audiences/reviewers often discuss |
| Open questions | uncertain facts, conflicting summaries, missing episodes |

Classify notes as:

- `confirmed`: source video/subtitles/official synopsis/consistent summaries
- `interpretation`: plausible explanation, not a fact
- `benchmark`: what other creators emphasize
- `open`: needs user confirmation or more source material

## 2. Benchmark Deconstruction

When the user asks for Douyin/Bilibili/YouTube style, or asks for a "爆款", analyze references as systems.

Extract:

- first frame and first sentence
- hook promise: what question makes viewers stay
- narration order: chronological, ending-first, crisis-first, clue-chain, protagonist confession
- turn cadence: how often a reversal/question/cost appears
- subtitle packaging: line length, emphasis words, position, color, outline
- shot density: approximate shots per 30 seconds
- audio design: BGM, sound hits, original dialogue bridges, silence
- ending strategy: emotional close, irony, sequel tease, thesis line

Rules:

- Do not copy competitor wording, unique title, thumbnail concept, or edit sequence.
- Do not reconstruct full competitor scripts from memory/transcripts.
- Use benchmarks to define constraints for the new original piece.

## 3. Original Script

Write the script after research and benchmark constraints.

For an 18-minute film explainer, target roughly 4500-6000 Chinese characters depending on voice speed and pauses.

Recommended structure:

| Section | Time | Job |
| --- | --- | --- |
| Cold open | 0:00-0:20 | danger, impossible result, shocking choice, or ending-first mystery |
| Lock-in | 0:20-1:30 | who the protagonist is, what they want, what traps them |
| Rule pressure | 1:30-4:00 | explain world/rules only after curiosity exists |
| Escalation | 4:00-8:00 | plans fail, enemy appears, cost rises |
| Midpoint reversal | 8:00-11:00 | reframe earlier clues |
| Truth chain | 11:00-15:00 | reveal cause, betrayal, hidden rule, or identity |
| Final choice | 15:00-17:20 | protagonist must pay a price |
| Closure | 17:20-18:00 | emotional landing and final thesis |

Each 15-25 seconds should open or close one viewer question.

## 4. Timed Subtitle And Shot-Intent Table

Before generating audio, convert the script into a production table:

| Edit Time | Subtitle/Narration | Planned Duration | Emotion | Connection | Visual Need | Source Candidate | Edit Method | Audio Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00:00-00:04 | 他醒来时，飞船已经把他判成死人。 | 4.0s | shock | hook | face + warning screen | source 00:43:10 | hard cuts + push-in | hit on "死人" |

Connection types:

- `suspense`: raises a question
- `answer`: resolves the prior question
- `reversal`: changes the meaning of prior facts
- `escalation`: makes danger worse
- `emotion`: lets a reaction breathe
- `reset`: transitions to a new chapter

Visual need types:

- `proof`: clue, file, subtitle, screen, object, wound
- `reaction`: face, hesitation, fear, decision
- `pressure`: alarm, enemy, countdown, locked door
- `action`: running, hiding, fighting, testing, escaping
- `consequence`: explosion, death, failure, system change
- `bridge`: external素材, map, news image, abstract transition

## 5. Audio First

Generate narration from beat-separated text. Measure real durations before final subtitle timing.

Guidelines:

- short hook lines can be 2-4 seconds
- normal lines should be 4-7 seconds
- split anything that exceeds 8 seconds
- leave 0.2-0.6 seconds for impact hits, reveals, or emotional reaction
- mark source-audio bridge beats where narration should stop and original audio should rise

If TTS timing and planned subtitles disagree, change the subtitle plan or regenerate audio. Do not force video to an inaccurate plan.

## 6. Visual Assembly

Find visuals after the timed subtitle table exists.

Rules:

- Source chronology is optional; narrative match is mandatory.
- A line about fear needs a face or body reaction.
- A line about a rule needs a screen, document, test, failed action, or consequence.
- A line about danger needs pressure, action, or consequence.
- A line about truth needs a clue before or during the reveal.
- External素材 can support mood, context, transition, internet/public background, or metaphor.
- External素材 cannot be used as proof that something happened in the story.

## 7. Review Gates

Before rendering full length:

1. Research brief has no unresolved plot-critical open questions.
2. Benchmark table has constraints, not copied lines.
3. First 30 seconds passes the hook test.
4. Subtitle table has emotion and visual needs for every beat.
5. Audio duration has been measured.
6. Every factual claim has a source or research basis.
7. External素材 is labeled and not misleading.

