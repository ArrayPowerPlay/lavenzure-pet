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
- **Outfits** (Settings → Outfit): pick the costume your pet wears. The current version ships the **Christmas outfit** (a knitted scarf, a snowy log and festive greetings) next to the normal look, and more outfits are planned.
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

## User guide

### The pet itself

| Action | Result |
|---|---|
| Left-click | A random reaction (a face, a line, a joke). It also clears an alert or a reminder that is waiting |
| Press and drag | Pick the pet up and carry it somewhere else; let go and it drops |
| Right-click | The pet menu (below) |
| Do nothing | It wanders, hops and flies around on its log on its own. Its eyes follow your mouse |

After **10 minutes** without touching the mouse or keyboard the pet dozes off. The first thing you do wakes it up and it says "Welcome back!" with how long you were away. From 20:00 to 05:00 it looks calmer and moves slower (it never goes to sleep because of the clock).

### The pet menu (right-click the pet)

| Item | What it does |
|---|---|
| **Chat** | Opens the chat bubble next to the pet |
| **Idle** | Makes the pet lie down and sleep until you choose **Wander** (the same item changes its name) |
| **Wander** | Wakes the pet up and lets it roam again |
| **Hide Pet** | Hides the pet. Chat, reminders and alerts keep working in the background |

### The tray icon (system tray, bottom-right of the taskbar)

The pet puts a small icon of itself in the system tray. On Windows 11 it may sit behind the **^** arrow; drag it out to keep it always visible. Right-click it:

| Item | What it does |
|---|---|
| **Show Pet** | Only appears while the pet is hidden: brings it back |
| **Settings** | Opens the Settings window (below) |
| **Quit App** | Closes Lavenzure completely |

If you cannot find the pet, it is probably hidden: use **Show Pet** from the tray icon.

### Chat

1. Right-click the pet → **Chat**. A speech bubble opens beside the pet and follows it when you drag it.
2. Type in the box at the bottom and press **Enter**. The reply streams in, and the pet makes a face that matches it.
3. Scroll up to re-read older messages. Press **Esc** or the **x** button to close the bubble.

Good to know:

- Write in any language: the pet answers in yours.
- The bubble closes itself after 30 seconds without chatting (it waits while your mouse rests on it).
- The conversation is kept in RAM only and is wiped after 15 minutes without chatting. Nothing is saved to disk.
- Chat needs an API key (see Settings → Chat AI). Without one the pet still runs; only the chat is off.

What you can ask (the AI decides which tool to use):

| Ask for | Example | Needs |
|---|---|---|
| Weather | "What's the weather in Hanoi?" | nothing (free) |
| Web search | "Search for the latest news about …" | a Tavily key (optional) |
| PC status | "How is my battery / CPU / RAM?" | nothing |
| A reminder | "Remind me at 11:00 to call mom" | nothing |

### Reminders

- Just ask in the chat: **"remind me in 30 minutes to stretch"** or **"remind me at 21:00 to submit the report"**. A time that has already passed today means tomorrow. Reminders can be up to 7 days ahead.
- If you give no time or a vague one ("tonight", "later"), the pet asks and suggests a time (morning 08:00, noon 12:00, afternoon 15:00, evening 20:00, late night 22:00).
- When a reminder is really set, a small note appears in the chat ("⏰ Reminder set: Today 21:00 · call mom"), so you can tell it was not just promised.
- Open the **Reminders** tab at the top of the chat bubble to see what is waiting (soonest first). Press the **x** next to one to remove it, or ask in the chat: "cancel the reminder about mom".
- When one goes off, the pet comes out even if it was hidden or asleep, shows an alarm clock and says the reminder in its own words. The bubble stays until you **left-click the pet**.
- Reminders are saved to disk, so they survive closing the app and restarting your PC. If a reminder's time passed while the app was closed, it goes off at the next start and says how many minutes late it is.

### Alerts and little talks

- **Alerts**: every 45 seconds the pet checks your PC. If the battery drops to 30% or lower, or CPU or RAM reach 90%, it shows an alert face and a bubble that stays until you left-click it. After you dismiss an alert it stays quiet for 10 minutes. The thresholds are in [`config.yaml`](./config.yaml).
- **Talks on its own**: about every 5 minutes it says a caring line (a good-morning wish, a reminder to rest…), a fun fact or a joke, taking turns. It stays quiet while it is hidden, asleep, or while you are chatting.

### Settings (tray icon → Settings)

Your choices are remembered between runs.

| Section | Options |
|---|---|
| **Language** | English or Tiếng Việt: what the pet says on screen (reactions, care lines, alerts, reminders). Chat replies follow the language you write in |
| **Outfit** | Normal or Christmas (knitted scarf, snowy log, now and then a festive greeting) |
| **Chat AI** | Choose **Gemini** or **OpenAI**, paste its API key and press **Save**: the key is verified first, then saved and works at once (**Show** / **Hide** reveals the key, **Remove** deletes it). An optional **Tavily** key switches on web search. Keys are stored in the Windows Credential Manager, never in a file |
| **Startup** | **Start with Windows**: the pet appears every time you log in (off by default) |
| **Performance** | Frame rate **30** or **60 fps**. 30 is lighter on your CPU/GPU; the line under it shows the real fps being drawn |

### Troubleshooting

- **The pet disappeared**: it is hidden; tray icon → **Show Pet**. If there is no tray icon, check the **^** arrow of the taskbar.
- **The chat says something went wrong**: check the key in Settings → Chat AI (**Save** tells you if the key is rejected), your internet connection and your API quota.
- **Starting Lavenzure a second time**: only one copy runs; launching it again just opens the chat of the one already running.
- **Anything else**: the log is `%LOCALAPPDATA%\Lavenzure\logs\lavenzure.log`.

## Run from source

Needs [uv](https://docs.astral.sh/uv/) on Windows (it also installs Python 3.13 for you).

```powershell
uv sync                    # creates .venv with the exact versions from uv.lock
uv run python src\main.py
```

For development you can put the keys in a `.env` file instead of Settings (`copy .env.example .env`); keys from `.env` or the environment override the saved ones.

```powershell
uv run pytest                           # tests (no display needed)
uv run ruff check .                     # lint
uv run python scripts\build.py          # build dist\Lavenzure-<version>-win-x64.zip
uv add <package>                        # add a dependency (updates pyproject.toml and uv.lock)
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
