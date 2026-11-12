# Calcifer Desktop Pet

[Tiếng Việt](./README_vi.md) · **English**

A little flame "pet" that lives on your Windows desktop, inspired by Calcifer (fan-art, drawn entirely in code). The flame wanders, floats and hops around the screen, reacts when you click or drag it, and opens a chat window (right-click) where you can talk to an AI agent that can use tools: weather, web search, timed reminders and PC status.

> **Personal use only.** Calcifer is a copyrighted Studio Ghibli character. This project is non-commercial fan-art, uses no original film assets, and must not be distributed publicly or commercially.

## Features

- **Character drawn entirely in code** (no image files): a three-layer red/orange/yellow flame with a dark maroon outline, a soft glow and drifting embers. The flame body is rendered with a GPU shader by default and automatically falls back to a CPU renderer if OpenGL 3.3 is unavailable.
- **Expressive face**: blinking, eyes that follow the mouse, eyelids, a talking mouth; happy, surprised, thinking and alert moods…
- **Moves on its own**: idles, walks along the bottom of the screen, floats, jumps — picked at random.
- **Always on top, transparent, click-through**: only the visible flame catches the mouse; the empty area around it passes clicks to the app underneath.
- **Mouse interaction**: left-click → a reaction plus a random line; press and drag → carry the pet; right-click → open the chat.
- **Speech bubbles follow the pet** as it moves.
- **Chat with an AI agent** (LangGraph + Google Gemini `gemini-flash-latest`) with 4 tools:
  - `weather` — current weather for a place name (Open-Meteo, no key needed)
  - `web_search` — web search (Tavily)
  - `set_timer_reminder` — "remind me to drink water in 10 minutes" (up to 24 hours)
  - `system_status` — current CPU / RAM / battery
- **Chat window** in warm flame colours, opens next to the pet, renders Markdown, closes with Esc; short replies also pop up in the bubble above the pet.
- **Clear error messages**: a missing/invalid key, exhausted quota, no internet… the pet explains it in the chat instead of failing silently or crashing.
- **Background monitoring**: alerts when battery < 30%, CPU > 90% or RAM > 90%; the alert stays until you click the pet.
- **Ambient lines**: after 15 minutes without interaction the pet says a random fact or joke.
- **Chat history lives in RAM only** and is wiped after 10 minutes of inactivity — nothing is written to disk.
- **System tray icon**: show/hide the pet, open the chat, quit. While the pet is hidden, reminders appear as tray notifications.
- **Single instance**: starting the app again just opens the running pet's chat window.

## Requirements

- Windows 10/11, single monitor.
- Python 3.13 (Windows build).
- A GPU with OpenGL 3.3 (optional — otherwise the fallback renderer is used).
- API keys:
  - `GEMINI_API_KEY` — from [Google AI Studio](https://aistudio.google.com/apikey) (needed for chat; without it the pet still runs, only the chat is unavailable).
  - `TAVILY_API_KEY` — from [tavily.com](https://tavily.com) (for the web search tool).

## Installation

Open PowerShell in the project folder:

```powershell
py -3.13 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env      # then open .env and fill in both API keys
```

## Running

```powershell
.venv-win\Scripts\python.exe src\main.py
```

Start automatically with Windows (creates a shortcut in the Startup folder that runs `pythonw.exe`, so no console window appears):

```powershell
.venv-win\Scripts\python.exe src\autostart\install_startup.py
```

To turn autostart off, delete `Calcifer.lnk` from `shell:startup` (type `shell:startup` in the Run dialog).

If something goes wrong, check the log file: `%LOCALAPPDATA%\Calcifer\logs\calcifer.log`.

## Usage

| Action | Result |
|---|---|
| Left-click the pet | It reacts and says a line; clears an active alert |
| Press and drag | Carry the pet somewhere else |
| Right-click the pet | Open the chat window |
| Esc in the chat window | Close the chat (history is kept for 10 minutes) |
| System tray icon | Show/hide the pet, open the chat, quit |

## Configuration

Non-secret settings live in [`config.yaml`](./config.yaml):

| Key | Meaning |
|---|---|
| `llm.model`, `llm.temperature` | Gemini model used for chat (default `gemini-flash-latest`) |
| `llm.timeout_seconds`, `llm.max_retries` | How long to wait / how often to retry before reporting an error |
| `character.scale` | Character size (0.75 = 150×177 px) |
| `character.fps` | Frames per second; lower it to 30 to save CPU |
| `character.flame_renderer` | Flame body renderer: `shader` (default, GPU) / `metaball` / `baked` |
| `behavior.state_weights` | How often the pet idles / walks / floats / jumps |
| `system_status.*` | Polling interval and alert thresholds |
| `ambient.random_fact_or_joke.idle_minutes` | Idle time before the pet says something on its own |
| `chat.reply_bubble_max_chars` | Replies up to this length also appear in the bubble (0 = off) |
| `memory.idle_timeout_minutes` | Idle time before the chat history is wiped |

Click reactions and the fact/joke pool live in `data/click_reactions.json` and `data/facts_jokes.json` (always in English).

## Development

The repo uses two virtual environments (neither is committed):

- `.venv-win` — Windows Python, used to run the real app. It can be called from WSL too; windows open on the Windows desktop.
- `.venv` — Linux Python (optional), only for quick animation previews through WSLg; don't use it to judge transparency or click-through.

```bash
.venv-win/Scripts/python.exe -m pip install -r requirements-dev.txt  # adds pytest + ruff
.venv-win/Scripts/python.exe -m pytest                            # run the tests (no display needed)
.venv-win/Scripts/python.exe -m ruff check .                      # lint
.venv-win/Scripts/python.exe src/character_preview.py [renderer]  # try every mood/motion, compare flame renderers
.venv-win/Scripts/python.exe src/bake_flame.py                    # regenerate the data for the `baked` renderer
QT_QPA_PLATFORM=offscreen WSLENV=QT_QPA_PLATFORM .venv-win/Scripts/python.exe src/main.py  # headless smoke run
```

Notes:

- `src/` is the import root (`import config`, `from overlay.x import ...`).
- When calling Windows Python from WSL, environment variables are only passed through if listed in `WSLENV` (as above).
- Keep each file's existing line endings (CRLF or LF) when editing.
- There is no packaged `.exe` yet (planned for later).

## Project layout

```
src/
├── main.py                 # entry point; wires all components together with Qt signals
├── config.py               # reads config.yaml + .env
├── app_logging.py          # logging to a rotating file
├── single_instance.py      # allows only one running pet
├── character_preview.py    # preview window for the character
├── bake_flame.py           # offline fire simulation for the `baked` renderer
├── overlay/                # pet window, character, face, 3 flame renderers, behavior, speech bubble
├── chat/                   # chat window
├── agent/                  # LangGraph agent, tools, session memory, error handling
├── monitor/                # system alerts, reminders, ambient lines
└── autostart/              # Windows Startup shortcut
tests/                      # automated tests (pytest)
data/                       # click reactions + fact/joke pool
assets/flame/               # pre-computed fire data for the `baked` renderer
```

## Design docs

The design documents are written in Vietnamese:

- [`CONTEXT.md`](./CONTEXT.md) — goals, architecture, locked technical decisions, change log.
- [`implementation_plan.md`](./implementation_plan.md) — progress and the **next-steps roadmap**.
- [`CLAUDE.md`](./CLAUDE.md) — guidance for AI coding agents working in this repo (English).
- [`ANIMATION_TUTORIAL.md`](./ANIMATION_TUTORIAL.md) — the abandoned PNG-cutout approach, kept for reference only.

## Status (2026-11-12)

- Character, movement, click/drag, tray icon, system monitoring and chat with all 4 tools work (chat moved to `gemini-flash-latest` after Google shut down `gemini-2.0-flash`).
- 46 automated tests and ruff linting.
- Still to do: long-term testing on the real desktop; tray extras and advanced animations (awaiting a decision); `.exe` packaging (later).
