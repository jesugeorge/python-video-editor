"""
AutoReel — Programmatic Video Editor
Author: Jesudas George
Description:
    A Python-based video automation tool that assembles multi-clip timelines,
    applies transitions, overlays animated text cards, adds audio fade-in/out,
    and exports a finished MP4 — all from a single JSON project file.

    Designed to demonstrate programmatic video production using MoviePy,
    equivalent to what tools like OpenShot and Shotcut do through their GUIs.

Usage:
    python video_editor.py --project project.json --output output.mp4
    python video_editor.py --demo                   # generates a demo video
"""

import argparse
import json
import os
import sys
import textwrap
from pathlib import Path
from typing import Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont

# MoviePy v2 imports
from moviepy import (
    VideoFileClip,
    AudioFileClip,
    ImageClip,
    TextClip,
    CompositeVideoClip,
    concatenate_videoclips,
    ColorClip,
)
from moviepy.video.fx import CrossFadeIn, CrossFadeOut, FadeIn, FadeOut


# ── Constants ─────────────────────────────────────────────────────────────────
DEFAULT_FPS        = 24
DEFAULT_RESOLUTION = (1280, 720)
TRANSITION_DURATION = 0.6   # seconds


# ── Colour helpers ────────────────────────────────────────────────────────────
def hex_to_rgb(hex_color: str) -> tuple:
    """Convert #RRGGBB to (R, G, B) tuple."""
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


# ── Title card generator ──────────────────────────────────────────────────────
def make_title_card(
    text: str,
    subtitle: str = "",
    duration: float = 3.0,
    resolution: tuple = DEFAULT_RESOLUTION,
    bg_color: str = "#0d0d1a",
    text_color: str = "#ffffff",
    accent_color: str = "#3ecfff",
) -> ImageClip:
    """
    Generate an animated title card as an ImageClip.
    Renders text onto a solid background with a coloured accent bar.
    """
    w, h = resolution
    bg_rgb      = hex_to_rgb(bg_color)
    text_rgb    = hex_to_rgb(text_color)
    accent_rgb  = hex_to_rgb(accent_color)

    img = Image.new("RGB", (w, h), bg_rgb)
    draw = ImageDraw.Draw(img)

    # accent bar
    bar_h = 4
    draw.rectangle([(80, h // 2 - 60), (w - 80, h // 2 - 60 + bar_h)],
                   fill=accent_rgb)

    # main title — wrap long lines
    lines = textwrap.wrap(text, width=40)
    y = h // 2 - 30
    for line in lines:
        # estimate centre (PIL default font is monospace ~6px wide per char)
        est_w = len(line) * 14
        draw.text(((w - est_w) // 2, y), line, fill=text_rgb)
        y += 30

    # subtitle
    if subtitle:
        sub_lines = textwrap.wrap(subtitle, width=60)
        y += 10
        for line in sub_lines:
            est_w = len(line) * 8
            draw.text(((w - est_w) // 2, y), line, fill=accent_rgb)
            y += 20

    arr = np.array(img)
    clip = ImageClip(arr, duration=duration)
    return clip


# ── Solid colour clip ─────────────────────────────────────────────────────────
def make_color_clip(
    color: str,
    duration: float,
    resolution: tuple = DEFAULT_RESOLUTION,
) -> ColorClip:
    return ColorClip(size=resolution, color=hex_to_rgb(color), duration=duration)


# ── Text overlay ──────────────────────────────────────────────────────────────
def make_lower_third(
    text: str,
    duration: float,
    resolution: tuple = DEFAULT_RESOLUTION,
    bg_color: str = "#0d0d1aCC",
    text_color: str = "#ffffff",
) -> ImageClip:
    """
    Renders a lower-third overlay bar with caption text.
    Returns a transparent-background ImageClip sized to full resolution
    (so it can be composited directly on top of another clip).
    """
    w, h = resolution
    bar_h = 60
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # semi-transparent bar at bottom
    bar_y = h - bar_h - 20
    draw.rectangle([(0, bar_y), (w, bar_y + bar_h)], fill=(13, 13, 26, 200))

    # text inside bar
    text_rgb = hex_to_rgb(text_color) + (255,)
    est_w = len(text) * 10
    draw.text((40, bar_y + 18), text, fill=text_rgb)

    arr = np.array(img)
    clip = ImageClip(arr, duration=duration, is_mask=False)
    return clip


# ── Transition helpers ────────────────────────────────────────────────────────
def apply_crossfade(clips: list, transition_dur: float = TRANSITION_DURATION) -> list:
    """
    Apply crossfade transitions between consecutive clips.
    Each clip (except the first) gets a CrossFadeIn effect and its
    start time is offset so it overlaps with the previous clip.
    """
    if len(clips) <= 1:
        return clips

    result = [clips[0]]
    t = clips[0].duration

    for clip in clips[1:]:
        faded = clip.with_effects([CrossFadeIn(transition_dur)])
        faded = faded.with_start(t - transition_dur)
        result.append(faded)
        t += clip.duration - transition_dur

    return result


# ── Project loader ────────────────────────────────────────────────────────────
def load_project(project_path: str) -> dict:
    """Load and validate a JSON project file."""
    with open(project_path) as f:
        proj = json.load(f)

    required = ["title", "clips"]
    for key in required:
        if key not in proj:
            raise ValueError(f"Project JSON missing required key: '{key}'")

    return proj


# ── Core render pipeline ──────────────────────────────────────────────────────
def render_project(project: dict, output_path: str) -> None:
    """
    Full render pipeline:
      1. Title card
      2. Per-clip processing (trim, lower-third overlay)
      3. Crossfade transitions
      4. Optional audio track with fade-in / fade-out
      5. Final composite + export
    """
    resolution = tuple(project.get("resolution", list(DEFAULT_RESOLUTION)))
    fps        = project.get("fps", DEFAULT_FPS)
    bg_color   = project.get("bg_color",     "#0d0d1a")
    accent     = project.get("accent_color", "#3ecfff")

    segments: list = []

    # 1. Title card ─────────────────────────────────────────────────────────
    title_dur = project.get("title_duration", 3.0)
    title_clip = make_title_card(
        text         = project["title"],
        subtitle     = project.get("subtitle", ""),
        duration     = title_dur,
        resolution   = resolution,
        bg_color     = bg_color,
        accent_color = accent,
    )
    title_clip = title_clip.with_effects([FadeIn(0.4), FadeOut(0.4)])
    segments.append(title_clip)

    # 2. Process each clip ──────────────────────────────────────────────────
    for i, clip_def in enumerate(project["clips"]):
        clip_type = clip_def.get("type", "video")

        if clip_type == "color":
            # solid colour filler clip
            base = make_color_clip(
                color      = clip_def.get("color", bg_color),
                duration   = clip_def.get("duration", 2.0),
                resolution = resolution,
            )

        elif clip_type == "title":
            base = make_title_card(
                text         = clip_def["text"],
                subtitle     = clip_def.get("subtitle", ""),
                duration     = clip_def.get("duration", 3.0),
                resolution   = resolution,
                bg_color     = clip_def.get("bg_color", bg_color),
                accent_color = clip_def.get("accent_color", accent),
            )

        elif clip_type == "video":
            src = clip_def.get("src", "")
            if not os.path.exists(src):
                print(f"  [warn] clip {i+1}: file not found '{src}', "
                      f"substituting colour placeholder.")
                base = make_color_clip(
                    color      = "#1a1a2e",
                    duration   = clip_def.get("duration", 3.0),
                    resolution = resolution,
                )
            else:
                base = VideoFileClip(src)
                # trim
                start = clip_def.get("start", 0)
                end   = clip_def.get("end",   base.duration)
                base  = base.subclipped(start, end)
                # resize if needed
                if tuple(base.size) != tuple(resolution):
                    base = base.resized(resolution)

        else:
            print(f"  [warn] unknown clip type '{clip_type}', skipping.")
            continue

        # lower-third caption overlay
        caption = clip_def.get("caption", "")
        if caption:
            overlay = make_lower_third(
                text       = caption,
                duration   = base.duration,
                resolution = resolution,
            )
            base = CompositeVideoClip([base, overlay])

        segments.append(base)

    # 3. End card ────────────────────────────────────────────────────────────
    end_text = project.get("end_card_text", "")
    if end_text:
        end_clip = make_title_card(
            text         = end_text,
            duration     = 2.5,
            resolution   = resolution,
            bg_color     = bg_color,
            accent_color = accent,
        )
        end_clip = end_clip.with_effects([FadeIn(0.3), FadeOut(0.5)])
        segments.append(end_clip)

    # 4. Crossfade transitions ───────────────────────────────────────────────
    segments = apply_crossfade(segments, transition_dur=TRANSITION_DURATION)

    # 5. Composite final timeline ────────────────────────────────────────────
    final = CompositeVideoClip(segments) if len(segments) > 1 else segments[0]

    # 6. Audio track ─────────────────────────────────────────────────────────
    audio_src = project.get("audio")
    if audio_src and os.path.exists(audio_src):
        print(f"  Adding audio track: {audio_src}")
        audio = AudioFileClip(audio_src)
        # loop or trim audio to match video length
        if audio.duration < final.duration:
            loops = int(final.duration / audio.duration) + 1
            audio = concatenate_videoclips([audio] * loops)
        audio = audio.subclipped(0, final.duration)
        audio = audio.with_effects([FadeIn(1.0), FadeOut(1.5)])
        final = final.with_audio(audio)

    # 7. Export ──────────────────────────────────────────────────────────────
    print(f"\nRendering → {output_path}")
    print(f"  Resolution : {resolution[0]}x{resolution[1]}")
    print(f"  FPS        : {fps}")
    print(f"  Segments   : {len(segments)}")
    print(f"  Duration   : {final.duration:.2f}s\n")

    final.write_videofile(
        output_path,
        fps     = fps,
        codec   = "libx264",
        audio_codec = "aac",
        logger  = "bar",
    )
    print(f"\nDone! Output saved to: {output_path}")


# ── Demo mode ─────────────────────────────────────────────────────────────────
DEMO_PROJECT = {
    "title"         : "AutoReel Demo",
    "subtitle"      : "Programmatic Video Editing with Python",
    "title_duration": 3.0,
    "end_card_text" : "Built with AutoReel",
    "bg_color"      : "#0d0d1a",
    "accent_color"  : "#3ecfff",
    "resolution"    : [1280, 720],
    "fps"           : 24,
    "clips": [
        {
            "type"    : "color",
            "color"   : "#1a1a2e",
            "duration": 2.5,
            "caption" : "Scene 1 — Solid colour clip with lower-third overlay"
        },
        {
            "type"    : "title",
            "text"    : "Chapter 2",
            "subtitle": "Programmatic title cards with accent bars",
            "duration": 3.0,
            "bg_color"      : "#0f0f23",
            "accent_color"  : "#ff6b6b"
        },
        {
            "type"    : "color",
            "color"   : "#0f2027",
            "duration": 2.5,
            "caption" : "Scene 3 — Crossfade transitions between every segment"
        },
        {
            "type"    : "title",
            "text"    : "Features",
            "subtitle": "Timeline assembly · Transitions · Text overlays · Audio fades",
            "duration": 3.5,
        },
        {
            "type"    : "color",
            "color"   : "#1a0a2e",
            "duration": 2.0,
            "caption" : "Render any project from a JSON file"
        },
    ]
}


def run_demo(output_path: str = "demo_output.mp4") -> None:
    print("Running AutoReel in demo mode…")
    render_project(DEMO_PROJECT, output_path)


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="AutoReel — Programmatic Video Editor"
    )
    parser.add_argument(
        "--project", "-p",
        help="Path to JSON project file"
    )
    parser.add_argument(
        "--output", "-o",
        default="output.mp4",
        help="Output video file path (default: output.mp4)"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate a demo video without a project file"
    )
    args = parser.parse_args()

    if args.demo:
        run_demo(args.output)
    elif args.project:
        project = load_project(args.project)
        render_project(project, args.output)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
