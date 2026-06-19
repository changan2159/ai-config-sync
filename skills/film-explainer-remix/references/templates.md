# Film Explainer Templates

## User Prompt Skeleton

```text
使用 film-explainer-remix 技能。
源视频：<path>
片名/剧名：<中文名 / 原名 / 年份，可选但强烈建议提供>
目标：中文主角视角影视解说短视频。
成片：<60-90秒风格样片 / 3-5分钟完整预览 / 8-12分钟中长版 / 18分钟长解说>
画幅：<横屏 / 竖屏9:16 / 先横屏样片>
参考风格：<可选，给3-5条抖音/B站/YouTube链接、标题、截图或文件>
输出：成片视频 + 旁白文本 + SRT/ASS + 镜头表 + beat JSON。

规则：
- 先联网/查资料建立完整剧情框架，再拆参考解说结构。
- 只学习竞品结构和节奏，不复制、不拼接、不洗稿。
- 先写原创文案，再做字幕时间轴，再配音，最后按字幕反找画面。
- 开场先抛危机/反常/结果，不做世界观开头。
- 每句旁白都要有画面证据。
- 关键句拆成2-5个镜头，不用长段原片硬贴。
- external素材只能做氛围、转场、隐喻，不能伪装成剧情证据。
```

## Retention Map

| Section | Target Time | Viewer Question | Protagonist State | Required Turn | Visual Evidence |
| --- | --- | --- | --- | --- | --- |
| First Frame | 0s | Why stop scrolling? | in danger / shocked / about to choose | contradiction | face, alarm, body, object |
| Hook | 0-8s | What happened? | forced into crisis | impossible result or deadline | fastest readable shots |
| Lock-In | 8-30s | Who is this about? | wants control/survival/truth | immediate obstacle | protagonist + location + threat |
| Rule | 30-60s | What are the rules? | tests world/system | rule with risk | screen, device, failed action |
| Escalation | 60-120s | Why is it worse? | makes first plan | plan fails or enemy appears | action + consequence |
| Reversal | 120-210s | What is the truth? | reinterprets clues | betrayal/hidden rule/cause | clue before reveal |
| Choice | 210-270s | What must be paid? | chooses cost | sacrifice or irreversible action | face + action + result |
| Closure | last 10-20s | What changed? | survives/loses/understands | emotional landing | quiet consequence |

## Research Brief

| Field | Content | Source / Confidence |
| --- | --- | --- |
| Title |  |  |
| Premise |  |  |
| Protagonist spine |  |  |
| Full plot frame |  |  |
| Ending explanation |  |  |
| Popular talking points |  |  |
| Open questions |  |  |

## Benchmark Table

| Reference | Hook | Narrative Order | Turn Cadence | Subtitle/Visual Packaging | Audio Pattern | Reusable Constraint |
| --- | --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |  |

## Timed Subtitle And Shot-Intent Table

| Edit Time | Subtitle/Narration | Duration | Emotion | Connection | Visual Need | Source Candidate | Edit Method | Audio Note |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 00:00-00:04 |  | 4.0s | shock | suspense | reaction + pressure | original 00:00:00 | hard cut + push-in | impact hit |

## Shot Table

| # | Edit Time | Source | Shot Role | Visual Content | Narration Function | Edit | Audio |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 0.0-1.2 | original 00:43:12 | pressure | red warning screen | instant danger | hard cut | alarm up |
| 2 | 1.2-2.4 | original 00:43:18 | reaction | protagonist freezes | stakes land | push-in | narration only |
| 3 | 2.4-3.6 | external素材 | bridge | countdown glitch | urgency reset | flash | impact hit |

## Beat JSON For Rendering

```json
[
  {
    "text": "她刚睁眼，飞船已经把她判成了最后一个活人。",
    "shots": [
      {"source_start": 2592.14, "duration": 1.2, "role": "reaction"},
      {"source_start": 2588.40, "duration": 1.0, "role": "pressure"},
      {"source_start": 2601.20, "duration": 1.5, "role": "proof"}
    ]
  },
  {
    "text": "更糟的是，警报不是故障，外面真的有东西撞上来了。",
    "shots": [
      {"source_start": 2610.00, "duration": 1.4, "role": "pressure"},
      {"source_start": 2620.50, "duration": 1.7, "role": "consequence"}
    ]
  }
]
```

Legacy single-shot beats are still valid:

```json
[
  {"duration": 4.5, "source_start": 2592.14, "text": "她刚睁眼，飞船已经把她判成了最后一个活人。"}
]
```

## SRT Rules

- Hook subtitle: 2.0-4.5 seconds.
- Normal subtitle: 4.0-7.0 seconds.
- Dense explanation: split instead of extending past 8 seconds.
- Reversal line: short, leave 0.2-0.6 seconds for visual or sound impact if possible.
- Each subtitle should be readable as one spoken breath.

## Delivery Table

| Output | Path | Notes |
| --- | --- | --- |
| Preview video | `<path>` | rendered result |
| Narration text | `<path>` | TTS source |
| SRT/ASS | `<path>` | subtitle timing/style |
| Beat JSON | `<path>` | source timecodes and shot roles |
| Diagnosis | inline | remaining risks and next iteration |
