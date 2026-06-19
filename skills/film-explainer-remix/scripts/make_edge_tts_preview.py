#!/usr/bin/env python3
"""Generate edge-tts narration and an ffmpeg preview from explainer beat JSON.

Supported beat formats:

Legacy single-shot:
[
  {"duration": 4.5, "source_start": 2592.14, "text": "The line..."}
]

Preferred multi-shot:
[
  {
    "text": "The line...",
    "shots": [
      {"source_start": 2592.14, "duration": 1.2, "role": "reaction"},
      {"source_start": 2588.40, "duration": 1.0, "role": "pressure"}
    ]
  }
]

Source-audio bridge:
[
  {
    "mode": "source_audio",
    "text": "",
    "source_subtitle": "Run!",
    "shots": [{"source_start": 120.5, "duration": 1.8, "role": "classic_line"}]
  }
]
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any


def run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=str(cwd), check=True)


def probe_source(video: Path) -> tuple[int, int, bool]:
    width = 1920
    height = 1080
    has_audio = True

    video_probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "csv=p=0:s=x",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = video_probe.stdout.strip()
    if "x" in raw:
        w, h = raw.split("x", 1)
        width = int(w)
        height = int(h)

    audio_probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "a",
            "-show_entries",
            "stream=index",
            "-of",
            "csv=p=0",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    has_audio = bool(audio_probe.stdout.strip())
    return width, height, has_audio


def probe_duration(media: Path) -> float:
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(media),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    raw = probe.stdout.strip()
    if not raw:
        raise ValueError(f"Could not read media duration: {media}")
    return float(raw)


def fmt_srt_time(seconds: float) -> str:
    ms_total = round(seconds * 1000)
    h, rem = divmod(ms_total, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def fmt_ass_time(seconds: float) -> str:
    cs_total = round(seconds * 100)
    h, rem = divmod(cs_total, 3600 * 100)
    m, rem = divmod(rem, 60 * 100)
    s, cs = divmod(rem, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def ass_text(text: str) -> str:
    return (
        text.replace("\\", "\\\\")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r\n", "\n")
        .replace("\n", r"\N")
    )


def ff_filter_quote(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", r"\'") + "'"


def normalize_beats(raw_beats: list[dict[str, Any]]) -> list[dict[str, Any]]:
    beats: list[dict[str, Any]] = []
    for beat_index, beat in enumerate(raw_beats, 1):
        mode = str(beat.get("mode", "narration")).strip() or "narration"
        if mode not in {"narration", "source_audio", "silence"}:
            raise ValueError(
                f"Beat {beat_index} has unsupported mode={mode!r}. "
                "Use narration, source_audio, or silence."
            )
        text = str(beat.get("text", "")).strip()
        source_subtitle = str(beat.get("source_subtitle", "")).strip()
        if mode == "narration" and not text:
            raise ValueError(f"Beat {beat_index} is missing text.")

        if "shots" in beat:
            raw_shots = beat.get("shots")
            if not isinstance(raw_shots, list) or not raw_shots:
                raise ValueError(f"Beat {beat_index} has an empty shots list.")
            shots = []
            for shot_index, shot in enumerate(raw_shots, 1):
                if shot.get("source", "original") not in ("original", None):
                    raise ValueError(
                        "This preview script only renders source-video shots. "
                        f"Beat {beat_index}, shot {shot_index} uses source={shot.get('source')!r}."
                    )
                if "source_start" not in shot or "duration" not in shot:
                    raise ValueError(
                        f"Beat {beat_index}, shot {shot_index} needs source_start and duration."
                    )
                duration = float(shot["duration"])
                if duration <= 0:
                    raise ValueError(f"Beat {beat_index}, shot {shot_index} has non-positive duration.")
                shots.append(
                    {
                        "source_start": float(shot["source_start"]),
                        "duration": duration,
                        "role": str(shot.get("role", "")),
                        "volume": str(shot.get("volume", "")),
                    }
                )
        else:
            if "source_start" not in beat or "duration" not in beat:
                raise ValueError(f"Beat {beat_index} needs either shots or source_start + duration.")
            duration = float(beat["duration"])
            if duration <= 0:
                raise ValueError(f"Beat {beat_index} has non-positive duration.")
            shots = [
                {
                    "source_start": float(beat["source_start"]),
                    "duration": duration,
                    "role": str(beat.get("role", "")),
                    "volume": str(beat.get("volume", "")),
                }
            ]

        planned_duration = sum(s["duration"] for s in shots)
        beats.append(
            {
                "text": text,
                "source_subtitle": source_subtitle,
                "mode": mode,
                "shots": shots,
                "planned_duration": planned_duration,
                "duration": planned_duration,
            }
        )
    return beats


def fit_shots_to_duration(beats: list[dict[str, Any]], min_shot_duration: float) -> None:
    for beat_index, beat in enumerate(beats, 1):
        target = float(beat["duration"])
        shots = beat["shots"]
        planned = sum(float(s["duration"]) for s in shots)
        if target <= 0:
            raise ValueError(f"Beat {beat_index} has non-positive target duration.")
        if planned <= 0:
            share = target / len(shots)
            for shot in shots:
                shot["duration"] = max(min_shot_duration, share)
            continue

        scale = target / planned
        for shot in shots:
            shot["planned_duration"] = float(shot["duration"])
            shot["duration"] = max(min_shot_duration, float(shot["duration"]) * scale)

        fitted = sum(float(s["duration"]) for s in shots)
        if fitted <= 0:
            raise ValueError(f"Beat {beat_index} could not be fitted to target duration.")
        shots[-1]["duration"] = max(min_shot_duration, float(shots[-1]["duration"]) + target - fitted)


def write_text_review(beats: list[dict[str, Any]], out_dir: Path, stem: str) -> Path:
    text_path = out_dir / f"{stem}_narration.txt"
    text_path.write_text(
        "\n".join(str(b["text"]) for b in beats if b.get("mode", "narration") == "narration"),
        encoding="utf-8",
    )
    return text_path


def generate_segmented_tts(
    beats: list[dict[str, Any]],
    out_dir: Path,
    stem: str,
    voice: str,
    rate: str,
    pause_after: float,
) -> Path:
    audio_parts: list[tuple[Path | None, float]] = []
    for index, beat in enumerate(beats, 1):
        if beat.get("mode", "narration") != "narration":
            beat["audio_duration"] = 0.0
            beat["pause_after"] = 0.0
            audio_parts.append((None, float(beat["duration"])))
            continue

        segment_text = out_dir / f"{stem}_beat_{index:03d}.txt"
        segment_audio = out_dir / f"{stem}_beat_{index:03d}.mp3"
        segment_text.write_text(str(beat["text"]), encoding="utf-8")
        run(
            [
                "edge-tts",
                "--voice",
                voice,
                "--rate",
                rate,
                "--file",
                str(segment_text),
                "--write-media",
                str(segment_audio),
            ],
            out_dir,
        )
        audio_duration = probe_duration(segment_audio)
        pause = pause_after if index < len(beats) else 0.0
        beat["audio_duration"] = audio_duration
        beat["pause_after"] = pause
        beat["duration"] = audio_duration + pause
        audio_parts.append((segment_audio, audio_duration))
        if pause > 0:
            audio_parts.append((None, pause))

    narration = out_dir / f"{stem}_narration.m4a"
    concat_audio_parts(audio_parts, narration, out_dir)
    return narration


def concat_audio_parts(parts: list[tuple[Path | None, float]], output: Path, cwd: Path) -> None:
    cmd = ["ffmpeg", "-y"]
    filters: list[str] = []
    labels: list[str] = []
    for index, (media, duration) in enumerate(parts):
        if media is None:
            cmd.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{duration:.3f}",
                    "-i",
                    "anullsrc=channel_layout=stereo:sample_rate=44100",
                ]
            )
        else:
            cmd.extend(["-i", str(media)])
        label = f"ac{index}"
        filters.append(
            f"[{index}:a]aresample=44100,aformat=sample_fmts=fltp:channel_layouts=stereo,"
            f"asetpts=PTS-STARTPTS[{label}]"
        )
        labels.append(f"[{label}]")

    filter_complex = ";".join(filters) + ";" + "".join(labels) + f"concat=n={len(parts)}:v=0:a=1[aout]"
    cmd.extend(["-filter_complex", filter_complex, "-map", "[aout]", "-c:a", "aac", "-b:a", "192k", str(output)])
    run(cmd, cwd)


def write_sync_report(beats: list[dict[str, Any]], out_dir: Path, stem: str) -> Path:
    report_path = out_dir / f"{stem}_sync_report.json"
    rows = []
    timeline = 0.0
    for index, beat in enumerate(beats, 1):
        planned = float(beat.get("planned_duration", beat["duration"]))
        audio = float(beat.get("audio_duration", beat["duration"]))
        render = float(beat["duration"])
        ratio = audio / planned if planned > 0 else None
        warning = None
        if beat.get("mode", "narration") == "narration":
            if ratio is not None and ratio > 1.35:
                warning = "narration_too_long"
            elif ratio is not None and ratio < 0.70:
                warning = "narration_too_short"
        rows.append(
            {
                "index": index,
                "mode": str(beat.get("mode", "narration")),
                "start": round(timeline, 3),
                "planned_duration": round(planned, 3),
                "audio_duration": round(audio, 3),
                "render_duration": round(render, 3),
                "ratio": round(ratio, 3) if ratio is not None else None,
                "warning": warning,
                "text": str(beat["text"]),
            }
        )
        timeline += render
    report_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path


def write_subtitles(
    beats: list[dict[str, Any]],
    out_dir: Path,
    stem: str,
    width: int,
    height: int,
    font_size: int,
    margin_v: int,
) -> tuple[Path, Path]:
    srt_path = out_dir / f"{stem}.srt"
    ass_path = out_dir / f"{stem}.ass"

    srt_blocks = []
    ass = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Narration,Microsoft YaHei,{font_size},&H00FFFFFF,&H000000FF,&H00000000,&HAA000000,1,0,0,0,100,100,0,0,1,4,0,2,80,80,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    cur = 0.0
    for i, beat in enumerate(beats, 1):
        if beat.get("mode", "narration") == "silence":
            cur += float(beat["duration"])
            continue
        subtitle_duration = float(beat.get("audio_duration", beat["duration"]))
        if beat.get("mode", "narration") == "source_audio":
            subtitle_duration = float(beat["duration"])
        end = cur + subtitle_duration
        text = str(beat.get("text") or beat.get("source_subtitle") or "").strip()
        if not text:
            cur += float(beat["duration"])
            continue
        srt_blocks.append(f"{i}\n{fmt_srt_time(cur)} --> {fmt_srt_time(end)}\n{text}\n")
        ass += f"Dialogue: 0,{fmt_ass_time(cur)},{fmt_ass_time(end)},Narration,,0,0,0,,{ass_text(text)}\n"
        cur += float(beat["duration"])

    srt_path.write_text("\n".join(srt_blocks), encoding="utf-8")
    ass_path.write_text(ass, encoding="utf-8")
    return srt_path, ass_path


def video_filter(index: int, start: float, end: float, layout: str, width: int, height: int) -> list[str]:
    base = f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS"
    if layout == "vertical-blur":
        return [
            f"{base},scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},gblur=sigma=24,eq=brightness=-0.10[bg{index}];",
            f"{base},scale={width}:-2:force_original_aspect_ratio=decrease[fg{index}];",
            f"[bg{index}][fg{index}]overlay=(W-w)/2:(H-h)/2,setsar=1,format=yuv420p[v{index}];",
        ]
    if layout == "vertical-crop":
        return [
            f"{base},scale={width}:{height}:force_original_aspect_ratio=increase,"
            f"crop={width}:{height},setsar=1,format=yuv420p[v{index}];"
        ]
    return [
        f"{base},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,format=yuv420p[v{index}];"
    ]


def build_filter(
    beats: list[dict[str, Any]],
    ass_path: Path,
    filter_path: Path,
    layout: str,
    width: int,
    height: int,
    has_audio: bool,
    original_volume: str,
    bridge_volume: str,
) -> None:
    lines: list[str] = []
    shot_index = 0
    for beat in beats:
        for shot in beat["shots"]:
            dur = float(shot["duration"])
            start = float(shot["source_start"])
            end = start + dur
            lines.extend(video_filter(shot_index, start, end, layout, width, height))
            if has_audio:
                volume = str(shot.get("volume") or (bridge_volume if beat.get("mode") == "source_audio" else original_volume))
                lines.append(
                    f"[0:a:0]atrim=start={start:.3f}:end={end:.3f},"
                    f"asetpts=PTS-STARTPTS,volume={volume}[a{shot_index}];"
                )
            else:
                lines.append(
                    f"anullsrc=channel_layout=stereo:sample_rate=44100,"
                    f"atrim=duration={dur:.3f}[a{shot_index}];"
                )
            shot_index += 1

    concat_inputs = "".join(f"[v{i}][a{i}]" for i in range(shot_index))
    ass_name = ff_filter_quote(ass_path.name)
    lines.append(
        f"{concat_inputs}concat=n={shot_index}:v=1:a=1[vraw][aorig];"
        f"[vraw]subtitles=filename={ass_name}[vsub];"
        f"[aorig][1:a]amix=inputs=2:duration=first:dropout_transition=0,volume=1.1[aout]"
    )
    filter_path.write_text("".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="Source video path.")
    parser.add_argument("--beats", required=True, help="Beat JSON path.")
    parser.add_argument("--out-dir", required=True, help="Output directory.")
    parser.add_argument("--stem", default="film_explainer_preview")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural")
    parser.add_argument("--rate", default="+10%")
    parser.add_argument("--original-volume", default="0.16")
    parser.add_argument("--bridge-volume", default="1.0")
    parser.add_argument(
        "--layout",
        choices=["horizontal", "vertical-blur", "vertical-crop"],
        default="horizontal",
    )
    parser.add_argument("--width", type=int)
    parser.add_argument("--height", type=int)
    parser.add_argument("--font-size", type=int)
    parser.add_argument("--subtitle-margin-v", type=int)
    parser.add_argument("--narration-audio", help="Use an existing narration file instead of generating edge-tts.")
    parser.add_argument(
        "--tts-mode",
        choices=["segmented", "single"],
        default="segmented",
        help="Segmented TTS measures each beat and keeps subtitles, voice, and video aligned.",
    )
    parser.add_argument("--pause-after", type=float, default=0.12, help="Silence after each segmented beat.")
    parser.add_argument("--min-shot-duration", type=float, default=0.25)
    args = parser.parse_args()

    video = Path(args.video)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_beats = json.loads(Path(args.beats).read_text(encoding="utf-8"))
    if not isinstance(raw_beats, list) or not raw_beats:
        raise ValueError("Beat JSON must be a non-empty list.")
    beats = normalize_beats(raw_beats)

    source_width, source_height, has_audio = probe_source(video)
    if args.layout == "horizontal":
        width = args.width or source_width
        height = args.height or source_height
        font_size = args.font_size or max(36, round(height * 0.052))
        margin_v = args.subtitle_margin_v or max(60, round(height * 0.11))
    else:
        width = args.width or 1080
        height = args.height or 1920
        font_size = args.font_size or 58
        margin_v = args.subtitle_margin_v or 280

    text_path = write_text_review(beats, out_dir, args.stem)
    narration = Path(args.narration_audio) if args.narration_audio else out_dir / f"{args.stem}_narration.mp3"
    filter_path = out_dir / f"{args.stem}_filter.txt"
    output = out_dir / f"{args.stem}.mp4"

    if not args.narration_audio:
        if args.tts_mode == "segmented":
            narration = generate_segmented_tts(
                beats=beats,
                out_dir=out_dir,
                stem=args.stem,
                voice=args.voice,
                rate=args.rate,
                pause_after=max(0.0, args.pause_after),
            )
        else:
            run(
                [
                    "edge-tts",
                    "--voice",
                    args.voice,
                    "--rate",
                    args.rate,
                    "--file",
                    str(text_path),
                    "--write-media",
                    str(narration),
                ],
                out_dir,
            )

    fit_shots_to_duration(beats, args.min_shot_duration)
    _srt_path, ass_path = write_subtitles(beats, out_dir, args.stem, width, height, font_size, margin_v)
    report_path = write_sync_report(beats, out_dir, args.stem)

    build_filter(
        beats=beats,
        ass_path=ass_path,
        filter_path=filter_path,
        layout=args.layout,
        width=width,
        height=height,
        has_audio=has_audio,
        original_volume=args.original_volume,
        bridge_volume=args.bridge_volume,
    )

    run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video),
            "-i",
            str(narration),
            "-/filter_complex",
            str(filter_path),
            "-map",
            "[vsub]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(output),
        ],
        out_dir,
    )
    print(output)
    print(report_path)


if __name__ == "__main__":
    main()
