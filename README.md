<p align="center">
  <img src="docs/images/hero.png" alt="The flame pet, grinning and looking up" width="260">
</p>

<h1 align="center">Lavenzure Desktop Pet</h1>

<p align="center">
  <em>A little fire demon that moves onto your desktop, and never sits still.</em><br>
  <a href="./README_vi.md">Tiếng Việt</a> · <b>English</b>
</p>

---

Lavenzure is a pocket-sized flame spirit that lives on top of your windows. It wanders around, hops, dozes off when you leave and reacts when you click or pick it up. Right-click it to chat: an AI answers in your language, checks the weather, searches the web, reminds you of things, and pulls a face that matches every reply.

<p align="center">
  <img src="docs/images/expressions.png" alt="Expressions: normal, happy, surprised, scared, angry, chill with a frying pan, yuck, asleep, riding the log">
</p>

**There is not a single image file in this character.** The fire, every blink and every grin is drawn in code, live, and never plays the same frame twice.

## Features

- **Alive on your desktop**: always on top, transparent, click-through everywhere except the flame. It idles, walks, flies around on a log, jumps, falls asleep after 10 minutes without you, and has a calmer look at night.
- **Expressive**: a GPU-shader flame and a face with real acting (the eyes follow your mouse; happy, surprised, scared, angry, chill, sleepy…).
- **Chat with an AI agent** (Google Gemini or OpenAI, your choice) with tools for **weather**, **web search**, **PC status** (CPU / RAM / battery) and **reminders** ("remind me at 11:00 to…").
- **Looks after you**: alerts when the battery, CPU or RAM get critical, and every 5 minutes it says a caring line, a fun fact or a joke.
- **English or Vietnamese** for everything it says (Settings).
- **Private**: the chat lives in RAM only, and your API keys are kept in the Windows Credential Manager.

## Download and run (Windows 10/11)

1. Download `Lavenzure-<version>-win-x64.zip` from the [Releases](../../releases) page and unzip it anywhere.
2. Double-click `Lavenzure.exe`. The pet appears and an icon shows up in the system tray.
3. Right-click the tray icon → **Settings**, pick your **Chat AI** and paste its API key. The key is checked first, then saved, and works at once.
   - **Gemini**: get a free key from [Google AI Studio](https://aistudio.google.com/apikey).
   - **OpenAI**: get a key from the [OpenAI platform](https://platform.openai.com/api-keys).
   - **Tavily** (optional, for web search): [tavily.com](https://tavily.com).
4. Optional: turn on **Start with Windows** in Settings.

Without a key the pet still runs; only the chat needs one.

> **Windows may warn you** ("Windows protected your PC") because the app is not code-signed. Click **More info → Run anyway**. Each release lists the SHA-256 of the zip so you can check your download (`Get-FileHash Lavenzure-<version>-win-x64.zip`).

## Using the pet

| Action | Result |
|---|---|
| Left-click | A random reaction (it also clears an alert or reminder) |
| Press and drag | Carry the pet somewhere else |
| Right-click | `Chat`, `Idle` (sleep) / `Wander`, `Hide Pet` |
| Tray icon | `Settings` (language, chat AI and keys, start with Windows, frame rate), `Show Pet`, `Quit App` |

Logs are in `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log`.

## Run from source

Needs Python 3.13 on Windows.

```powershell
py -3.13 -m venv .venv-win
.venv-win\Scripts\python.exe -m pip install -r requirements.txt
.venv-win\Scripts\python.exe src\main.py
```

For development you can put the keys in a `.env` file instead of Settings (`copy .env.example .env`); keys from `.env` or the environment override the saved ones.

```powershell
.venv-win\Scripts\python.exe -m pip install -r requirements-dev.txt   # pytest, ruff, pyinstaller
.venv-win\Scripts\python.exe -m pytest                                 # tests (no display needed)
.venv-win\Scripts\python.exe -m ruff check .                           # lint
.venv-win\Scripts\python.exe scripts\build.py                          # build dist\Lavenzure-<version>-win-x64.zip
```

Settings you may want to change live in [`config.yaml`](./config.yaml) (character size, frame rate, flame renderer, alert thresholds, AI models, how often the pet talks). Your own choices from the Settings window are saved in `%LOCALAPPDATA%\Lavenzure\settings.json`.

Releases are made by pushing a tag such as `v0.1.0` (see `.github/workflows/release.yml`); the version number always comes from the git tag.

## Project layout

```
src/
├── main.py            # entry point; wires everything together with Qt signals
├── overlay/           # pet window, character, face, flame renderers, behavior, speech bubble
├── chat/              # chat bubble
├── agent/             # LangGraph agent (Gemini / OpenAI), tools, key checks, session memory
├── monitor/           # system alerts, reminders, ambient lines, idle / night
├── ui/                # menus, tray icon, Settings window
└── api_keys.py, version.py, paths.py, autostart/ ...
tests/  data/  assets/  scripts/  docs/
```

The design documents in [`docs/`](./docs) (decisions, plan, test checklist) are written in Vietnamese; [`CLAUDE.md`](./CLAUDE.md) and the [`pet-animation` skill](./.claude/skills/pet-animation/SKILL.md) guide AI coding agents working in this repo.

## License

Free and non-commercial, released under the [MIT License](./LICENSE). Lavenzure is inspired by Calcifer, a Studio Ghibli character; this is an unofficial fan work that uses no original film assets and is not affiliated with Studio Ghibli.
