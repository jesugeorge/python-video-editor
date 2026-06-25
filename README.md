# AutoReel — Programmatic Video Editor

A Python-based video automation tool that assembles multi-clip timelines, applies crossfade transitions, overlays animated text cards, adds audio fade-in/out, and exports a finished MP4 — all driven from a single JSON project file.

Built as a portfolio project demonstrating programmatic video production, equivalent to what GUI tools like **OpenShot** and **Shotcut** do visually — but fully automated through code.

---

## Demo Output

Running `python video_editor.py --demo` generates a **15-second, 1280×720 MP4** with:
- Animated title card with accent bar
- 5 content segments with lower-third captions
- Crossfade transitions between every segment
- Closing end card with fade-out

---

## Features

- **Title cards** — programmatically rendered with customisable background colour, accent bar, and subtitle
- **Lower-third overlays** — semi-transparent caption bars composited over any clip
- **Crossfade transitions** — smooth overlap transitions between all timeline segments
- **Audio track support** — attach a background music file with automatic fade-in and fade-out; audio loops or trims to match video length
- **JSON project files** — define your entire video (clips, captions, colours, audio, resolution, FPS) in a single config file
- **Graceful fallback** — missing video files are automatically replaced with colour placeholder clips so renders never fail mid-pipeline
- **Clip types supported:** `video` (with trim), `title` (generated card), `color` (solid filler)

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/jesugeorge/python-video-editor.git
cd python-video-editor

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the built-in demo (no video files needed)
python video_editor.py --demo --output demo_output.mp4

# 4. Or render your own project
python video_editor.py --project project.json --output my_video.mp4
```

---

## Project JSON Format

```json
{
  "title": "My Video",
  "subtitle": "Created with AutoReel",
  "title_duration": 3.5,
  "end_card_text": "Thank you for watching",
  "bg_color": "#0d0d1a",
  "accent_color": "#3ecfff",
  "resolution": [1280, 720],
  "fps": 24,
  "audio": "background_music.mp3",
  "clips": [
    {
      "type": "video",
      "src": "clip1.mp4",
      "start": 0,
      "end": 10,
      "caption": "Opening scene"
    },
    {
      "type": "title",
      "text": "Chapter 1",
      "subtitle": "The Beginning",
      "duration": 3.0,
      "accent_color": "#ff6b6b"
    },
    {
      "type": "color",
      "color": "#1a1a2e",
      "duration": 2.0,
      "caption": "Transition segment"
    }
  ]
}
```

### Clip Types

| Type | Required Fields | Description |
|---|---|---|
| `video` | `src` | Trims and embeds an existing video file |
| `title` | `text` | Generates an animated title card |
| `color` | `color`, `duration` | Solid colour filler clip |

All clip types support the optional `caption` field for lower-third overlays.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| Video processing | MoviePy 2.0 |
| Image rendering | Pillow (PIL) |
| Numerical ops | NumPy |
| Output codec | H.264 (libx264) + AAC audio |

---

## Project Structure

```
python-video-editor/
├── video_editor.py    # Full pipeline — rendering, transitions, overlays, export
├── project.json       # Example project file
├── requirements.txt   # Python dependencies
└── README.md
```

---

## Design Decisions

- **JSON-driven pipeline** — separating content definition from rendering logic makes the tool reusable across any video project without code changes.
- **Crossfade via clip overlap** — transitions are implemented by offsetting clip start times and applying `CrossFadeIn` effects, matching how non-linear editors like OpenShot handle transitions internally.
- **Graceful fallback on missing files** — missing video sources substitute colour placeholders automatically, so a partial asset set never breaks a render pipeline.
- **Pillow for title card rendering** — custom title cards are rendered frame-by-frame as NumPy arrays, giving full control over layout, typography, and colour without requiring external font assets.
- **Audio looping** — background music shorter than the video is looped and trimmed automatically, avoiding silent gaps in longer timelines.

---

## Author

**Jesudas George**
- GitHub: [github.com/jesugeorge](https://github.com/jesugeorge)
- LinkedIn: [linkedin.com/in/jesudas-george](https://linkedin.com/in/jesudas-george)
