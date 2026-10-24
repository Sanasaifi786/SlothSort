# 🦥 SlothSort

**A lazy, private, offline file tidier. A local open-weight AI sorts and renames your messy Downloads folder so you don't have to.**

> Built for the **Hacktoberfest 2026 Open-Source AI Challenge, Week 3: "Slow and Steady"**
> Theme: build something with open-source AI that rewards laziness.

---

## Table of contents

1. [What is SlothSort?](#1-what-is-slothsort)
2. [Why open-source AI?](#2-why-open-source-ai)
3. [Features](#3-features)
4. [Requirements](#4-requirements)
5. [Tech stack](#5-tech-stack)
6. [How it works](#6-how-it-works)
7. [Folder structure](#7-folder-structure)
8. [Setup (Windows)](#8-setup-windows)
9. [Usage](#9-usage)
10. [Configuration](#10-configuration)
11. [Safety design](#11-safety-design)
12. [How to test](#12-how-to-test)
13. [Benchmark (the "lazy payoff")](#13-benchmark-the-lazy-payoff)
14. [Build plan, step by step](#14-build-plan-step-by-step)
15. [Known limitations](#15-known-limitations)
16. [Roadmap](#16-roadmap)
17. [Challenge submission checklist](#17-challenge-submission-checklist)
18. [Project notes (delete before publishing)](#18-project-notes-delete-before-publishing)
19. [License and credits](#19-license-and-credits)

---

## 1. What is SlothSort?

Everyone has a Downloads folder full of `final_FINAL(3).pdf` and `IMG_2231.jpg`. Cleaning it is a task nobody wants to do.

SlothSort scans a folder, asks a **small AI model running on your own laptop** what each file is, then sorts and renames it:

| Before | After |
|---|---|
| `Airtel_bill_oct(3).pdf` | `Bills/2026-10 Airtel bill.pdf` |
| `DS_unit3_notes_final.pdf` | `Study/DS unit 3 notes.pdf` |
| `IMG_2231.jpg` | `Photos/IMG_2231.jpg` |
| `vscode_setup.exe` | `Installers/vscode_setup.exe` |
| `resume_v7.docx` | `Career/Resume v7.docx` |

You run one command, look at the plan, approve it, and you're done. Every move can be undone.

## 2. Why open-source AI?

This is the part the challenge asks us to explain. For this tool, an open model beats a closed API because:

- **Privacy:** your bills, resumes, and ID scans never leave your laptop.
- **Offline:** it works with no internet.
- **Free forever:** no API key, no per-file cost, no usage limits.
- **Swappable:** change the model with one flag (`--model`) and compare results.
- **Tunable:** categories and prompts are plain files you control.

Honest trade-offs: a small local model is slower and sometimes less accurate than a large cloud model. SlothSort reduces this with a rules-first design (see section 6) and measures accuracy openly (section 13).

## 3. Features

- 🧠 Local AI classification (Gemma via Ollama), no cloud calls
- ⚡ **Hybrid mode:** fast rules for obvious files, AI only for ambiguous ones
- 🔍 **Dry-run by default:** nothing moves until you pass `--apply`
- ↩️ **Undo:** every run writes a log, and `slothsort undo` reverses it
- 🛡️ Never deletes files, only moves them
- 📁 Configurable categories (`categories.json`)
- 🧹 Skips files still downloading (`.crdownload`, `.part`, `.tmp`) and files modified in the last few minutes
- 🔁 Handles name clashes and Windows-illegal characters
- 📊 Built-in benchmark script to measure accuracy and time saved

## 4. Requirements

- Windows 10/11, 16 GB RAM (tested target)
- Python 3.10 or newer
- [Ollama](https://ollama.com) installed and running
- A small Gemma model pulled in Ollama (about 3 GB disk for the 4B model)
- Git (to clone and publish)
- No GPU needed. A CPU is fine for the 4B model, just slower.

## 5. Tech stack

| Part | Technology | Why |
|---|---|---|
| Language | Python 3.10+ | Simple, great file libraries |
| Local model runner | **Ollama** | Easiest way to run open models on Windows |
| Model | **Gemma 3 4B** (open-weight) | Fits 16 GB RAM, good enough for classification |
| Model client | `ollama` Python package | Few lines to call the model |
| PDF text | `pypdf` | Read the first page of a PDF |
| Word text | `python-docx` | Read the first lines of a `.docx` |
| CLI | `argparse` (built in) | No extra dependency |
| Console output | `rich` (optional) | Readable tables in the terminal |
| Tests | `pytest` | Standard Python testing |
| Hosting | GitHub (public repo, MIT license) | Required for the submission |

## 6. How it works

```
                 ┌───────────────┐
 folder  ──────► │ 1. Scan files │  skip subfolders, temp files, recent files
                 └──────┬────────┘
                        ▼
                 ┌───────────────┐
                 │ 2. Rules pass │  .jpg/.png → Photos, .exe/.msi → Installers ...
                 └──────┬────────┘
              obvious ◄─┴─► ambiguous (pdf, docx, txt, unknown)
                 │              ▼
                 │       ┌──────────────────┐
                 │       │ 3. Extract text  │  first ~500 characters
                 │       └──────┬───────────┘
                 │              ▼
                 │       ┌──────────────────┐
                 │       │ 4. Local AI call │  Gemma via Ollama → JSON
                 │       └──────┬───────────┘
                 ▼              ▼
              ┌────────────────────────┐
              │ 5. Build plan (table)  │  old path → new path
              └──────────┬─────────────┘
                         ▼
              ┌────────────────────────┐
              │ 6. Dry-run: print only │  or --apply: move + write undo log
              └────────────────────────┘
```

**Why hybrid?** Asking the AI about every photo and installer is slow and pointless. Rules handle roughly 60–70% of a typical Downloads folder instantly. The AI is used only where it actually helps: documents whose names say nothing.

**The AI call** asks for strict JSON:

```python
import json
import ollama

PROMPT = """You organise files. Choose ONE category from: {categories}.
Also suggest a short, clean file name (no extension, max 6 words).
File name: {name}
Start of content: {snippet}
Reply ONLY as JSON: {{"category": "...", "new_name": "..."}}"""

def classify(name: str, snippet: str, categories: list[str], model: str) -> dict:
    reply = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": PROMPT.format(
            categories=", ".join(categories), name=name, snippet=snippet[:500])}],
        format="json",
        options={"temperature": 0},
    )
    data = json.loads(reply["message"]["content"])
    if data.get("category") not in categories:   # never trust the model blindly
        data["category"] = "Other"
    return data
```

Key habit: **validate everything the model returns.** If the category isn't in your list, fall back to `Other`. If JSON fails to parse, fall back to the rules result.

## 7. Folder structure

```
slothsort/
├── README.md
├── LICENSE                  # MIT
├── requirements.txt
├── .gitignore
├── categories.json          # categories, extension rules, prompt settings
├── slothsort/
│   ├── __init__.py
│   ├── cli.py               # command line: scan / apply / undo
│   ├── scanner.py           # find eligible files, skip temp/recent
│   ├── rules.py             # extension → category rules
│   ├── extract.py           # read first text from pdf/docx/txt
│   ├── ai.py                # Ollama call + JSON validation
│   ├── planner.py           # combine rules + AI into a move plan
│   ├── mover.py             # safe moves, name clashes, undo log
│   └── utils.py             # sanitize file names, date helpers
├── tests/
│   ├── test_rules.py
│   ├── test_utils.py        # file-name sanitizing
│   ├── test_mover.py        # moves + undo (uses temp folders)
│   └── test_ai_parsing.py   # bad JSON, unknown category
├── scripts/
│   ├── make_test_folder.py  # builds ~40 fake messy files + labels.csv
│   └── benchmark.py         # accuracy + time: rules-only vs hybrid
└── docs/
    ├── demo.gif
    └── benchmark.md
```

## 8. Setup (Windows)

Open **PowerShell** and run:

```powershell
# 1. Install Ollama from https://ollama.com, then check it:
ollama --version

# 2. Download the model (about 3 GB). Check ollama.com/library for the newest small Gemma.
ollama pull gemma3:4b

# 3. Quick test that the model answers
ollama run gemma3:4b "Reply with the word ready"

# 4. Get the project
git clone https://github.com/<your-username>/slothsort.git
cd slothsort

# 5. Create a virtual environment and install packages
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If PowerShell blocks the activate script, run
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

`requirements.txt`:

```
ollama
pypdf
python-docx
rich
pytest
```

## 9. Usage

```powershell
# Preview only (safe, nothing is moved)
python -m slothsort "C:\Users\<you>\Downloads"

# Actually do it
python -m slothsort "C:\Users\<you>\Downloads" --apply

# Rules only, no AI (fastest)
python -m slothsort "C:\Users\<you>\Downloads" --no-ai

# Use another model
python -m slothsort "C:\Users\<you>\Downloads" --model gemma3:12b

# Undo the last run
python -m slothsort undo "C:\Users\<you>\Downloads"
```

Always try it on a **copy** or the generated test folder first.

## 10. Configuration

`categories.json`:

```json
{
  "categories": ["Bills", "Study", "Career", "Photos", "Installers", "Documents", "Other"],
  "extension_rules": {
    "Photos": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"],
    "Installers": [".exe", ".msi", ".dmg"],
    "Archives": [".zip", ".rar", ".7z"]
  },
  "skip_extensions": [".crdownload", ".part", ".tmp"],
  "skip_if_modified_within_minutes": 10,
  "default_model": "gemma3:4b"
}
```

Edit it freely. Add a category and the AI will start using it.

## 11. Safety design

These rules are non-negotiable, because a file tool that loses files is worse than no tool:

1. **Dry-run is the default.** Moving needs an explicit `--apply`.
2. **Never delete.** Only `shutil.move` inside the chosen folder.
3. **Undo log.** Each run saves `slothsort_undo.json` listing every `old → new` path.
4. **No overwrites.** If the target exists, add ` (2)`, ` (3)` and so on.
5. **Top level only.** Subfolders are never touched.
6. **Skip active downloads** and files changed in the last 10 minutes.
7. **Sanitize names:** remove `<>:"/\|?*` and trailing dots or spaces, and limit length.
8. **Model output is untrusted.** Validate the category; never build a path from raw model text.

## 12. How to test

**Automated tests:**

```powershell
pytest -q
```

What the tests cover:
- Rules map extensions to the right category
- File-name sanitizing handles illegal characters and long names
- Mover creates folders, handles name clashes, and **undo restores the exact original state**
- AI parsing survives bad JSON and unknown categories (use a fake model function, no Ollama needed)

**Manual test with fake messy files:**

```powershell
python scripts/make_test_folder.py        # creates .\test_downloads with ~40 files and labels.csv
python -m slothsort .\test_downloads      # dry-run: read the plan
python -m slothsort .\test_downloads --apply
python -m slothsort undo .\test_downloads # confirm everything returns
```

**Checklist before you call it done:**
- [ ] Dry-run changes nothing on disk
- [ ] `--apply` produces the planned layout
- [ ] `undo` restores every file
- [ ] A file with illegal characters is handled
- [ ] Two files with the same target name don't overwrite each other
- [ ] Works with Wi-Fi turned **off** (proves it's offline)
- [ ] An empty folder and a folder with only subfolders don't crash

## 13. Benchmark (the "lazy payoff")

This is your strongest piece of evidence in the blog post.

`scripts/make_test_folder.py` also writes `labels.csv` with the *correct* category for each fake file. `scripts/benchmark.py` then compares:

| Mode | Files | Correct | Accuracy | Time |
|---|---|---|---|---|
| Rules only | 40 | _fill in_ | _fill in_ | _fill in_ |
| Hybrid (rules + Gemma 4B) | 40 | _fill in_ | _fill in_ | _fill in_ |
| Manual (you, with a stopwatch) | 40 | 40 | 100% | _fill in_ |

Report the real numbers, including where it failed. Honest results make the post credible.

## 14. Build plan, step by step

### Friday, Oct 23: get the core working

1. Create a public GitHub repo named `slothsort` with a README and MIT license. **It must be a new project started this week.**
2. Install Ollama, run `ollama pull gemma3:4b`, and confirm `ollama run` answers.
3. Create the folder structure above and `requirements.txt`.
4. Write `utils.py` (sanitize names) and `rules.py` (extension rules). Test them.
5. Write `scanner.py`: list top-level files, skip temp and recent ones.
6. Write `ai.py` with the `classify` function. Test it on 5 sample files by hand.
7. Write `planner.py` and `cli.py` so a **dry-run prints a plan table**. Commit.

### Saturday, Oct 24: make it real and measure it

1. Write `extract.py` (pdf, docx, txt snippets).
2. Write `mover.py`: moving, name clashes, undo log, and the `undo` command.
3. Write the tests, then run `pytest`.
4. Run `make_test_folder.py` and then `benchmark.py`. Save the numbers.
5. Test with Wi-Fi off. Fix bugs.
6. Record the demo (see below).

### Sunday, Oct 25: write and submit

1. Finish this README (fill in the benchmark table, add the demo GIF).
2. Write the DEV post using the Week 3 template.
3. Publish **by Sunday evening IST**. The official cutoff is Oct 25, 11:59 PM PDT (about 12:29 PM IST on Oct 26), but don't gamble on it.

### Demo recording (1–2 minutes)

1. Show the messy folder.
2. Run the dry-run and show the plan.
3. Run `--apply` and show the tidy result.
4. Run `undo` and show it come back.
5. Show Wi-Fi off and say "no internet needed".

Use Windows Game Bar (`Win + G`) or OBS Studio. Upload to YouTube (unlisted) or attach a GIF.

### If you run short on time

Cut in this order: watch mode, docx support, rich tables. **Never cut:** dry-run, undo, tests, and the benchmark numbers.

## 15. Known limitations

- Small local models can mislabel ambiguous files. Rules plus validation reduce this, but not to zero.
- Scanned PDFs and images have no extractable text. They are sorted by name and extension only.
- Speed depends on your CPU. Expect about a few seconds per AI-classified file on a laptop without a GPU.
- Only top-level files are processed. Nested folders are out of scope.
- Tested mainly on Windows.

## 16. Roadmap

- Watch mode: tidy new downloads automatically in the background
- OCR for scanned PDFs and screenshots using an open-source OCR tool
- A small local web UI (Streamlit) to approve or reject each move
- Learn from corrections: remember "this sender's PDFs always go to Bills"
- Compare multiple open models in one benchmark

## 17. Challenge submission checklist

- [ ] Repo is public and was created this week (Oct 19–25)
- [ ] README has the demo, setup, and honest limitations
- [ ] Post uses the official template, with tags `devchallenge` and `hf26challenge`
- [ ] Post sections: What I Built, Demo, Code, How I Built It, Why Open Innovation Matters, The Lazy Payoff
- [ ] Prize Categories lists only partners actually used (for example **Gemma**)
- [ ] Any borrowed code is credited
- [ ] Post is **published** (not a draft), once only
- [ ] DEV account is connected at hacktoberfest.com/my

## 18. Project notes (delete before publishing)

**Is this good enough?** Yes for a valid, complete entry, and a completion badge only needs a valid submission. For a *prize*, note that "file and inbox tidier" is one of the four ideas listed in the challenge text, so many people will build something similar. What separates entries is execution and writing.

**What makes this version stand out:**
1. Safety first: dry-run, undo, and never deleting, so it is trustworthy.
2. Hybrid rules-plus-AI design with a stated reason.
3. Real benchmark numbers, including failures.
4. Clear offline and privacy proof.
5. A readable, honest write-up.

**Alternatives if you want a different angle:**
- **College-notice digest:** feed in an exported WhatsApp chat or notice text and get a 5-line summary plus deadlines. Strong privacy story, but harder to prove accuracy.
- **Notes to flashcards:** turn a PDF of notes into flashcards offline. Good for students, but crowded.
- **Receipt reader:** pull amount, date and vendor from bills into a CSV. More technical depth, but riskier in three days.

SlothSort is the most realistic one to finish well in the time left.

## 19. License and credits

MIT License. Built with [Ollama](https://ollama.com) and [Gemma](https://ai.google.dev/gemma).
Credit any code or ideas borrowed from other projects here.#   S l o t h S o r t  
 