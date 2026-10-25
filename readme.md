# 🦥 SlothSort

<div align="center">

**A lazy, private, offline file tidier. A local open-weight AI sorts and renames your messy Downloads folder so you don't have to.**

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Model](https://img.shields.io/badge/Model-Gemma%203%204B-4285F4?logo=google&logoColor=white)](https://ai.google.dev/gemma)
[![Runner](https://img.shields.io/badge/Runner-Ollama-black?logo=ollama&logoColor=white)](https://ollama.com)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-success)](https://github.com)
[![Tests](https://img.shields.io/badge/Tests-33%20Passing-brightgreen)](tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hacktoberfest](https://img.shields.io/badge/Hacktoberfest-2026%20Challenge-FF8AE2?logo=hacktoberfest&logoColor=white)](https://hacktoberfest.com/)

*Built for the **Hacktoberfest 2026 Open-Source AI Challenge, Week 3: "Slow and Steady"***  
*Theme: Build something with open-source AI that rewards laziness.*

</div>

---

## 📑 Table of Contents

1. [The Problem & The Solution](#1-the-problem--the-solution)
2. [Why Open-Source AI? (Privacy & Offline)](#2-why-open-source-ai-privacy--offline)
3. [Architecture: The Hybrid Rules-First Engine](#3-architecture-the-hybrid-rules-first-engine)
4. [Safety Non-Negotiables](#4-safety-non-negotiables)
5. [The "Lazy Payoff" Benchmark](#5-the-lazy-payoff-benchmark)
6. [Tech Stack](#6-tech-stack)
7. [Installation & Setup](#7-installation--setup)
8. [CLI Usage](#8-cli-usage)
9. [Configuration](#9-configuration)
10. [Automated Testing](#10-automated-testing)
11. [How Judges Can Test Offline](#11-how-judges-can-test-offline)
12. [Known Limitations & Roadmap](#12-known-limitations--roadmap)
13. [License & Acknowledgments](#13-license--acknowledgments)

---

## 1. The Problem & The Solution

Everyone's `Downloads` folder is a chaotic digital junk drawer filled with cryptic names like `Airtel_bill_oct(3).pdf`, `IMG_2231.jpg`, and `resume_v7_updated_final.docx`. Manually sorting, classifying, and renaming dozens of files is tedious work nobody wants to do.

**SlothSort solves this with one command.** It scans the target folder, uses fast deterministic rules for obvious files, reads small content snippets of ambiguous documents, and asks a **local Google Gemma 3 model running on your own machine** to classify and smartly rename them:

| Messy File Name | SlothSort Destination | Engine |
|---|---|:---:|
| `Airtel_bill_oct(3).pdf` | `Bills/2026-10 Airtel Broadband Bill.pdf` | 🧠 AI |
| `DS_unit3_notes_final.pdf` | `Study/Data Structures Unit 3 Notes.pdf` | 🧠 AI |
| `IMG_2231.jpg` | `Photos/IMG_2231.jpg` | ⚡ Rule |
| `vscode_setup_x64.exe` | `Installers/vscode_setup_x64.exe` | ⚡ Rule |
| `resume_v7_updated_final.docx` | `Career/Senior Software Resume.docx` | 🧠 AI |
| `dataset_photos_raw.7z` | `Archives/dataset_photos_raw.7z` | ⚡ Rule |

**Dry-run by default.** You see a preview table first. Nothing changes on disk until you pass `--apply`. And if you change your mind, a single `undo` command reverses every single move.

---

## 2. Why Open-Source AI? (Privacy & Offline)

For file organization, **local open-weight AI beats cloud APIs across every metric that matters**:

- 🔒 **Zero Data Leakage:** Your tax forms, medical records, bank statements, and resumes never leave your RAM. No cloud provider trains on your documents.
- 📴 **100% Offline Capability:** Works on an airplane, in a remote cabin, or with Wi-Fi completely switched off.
- 💸 **Zero Cost Forever:** No API credits, token billing, or subscription paywalls.
- 🔄 **Model Swappable:** Seamlessly swap models via the CLI (`--model gemma3:4b`, `--model llama3.2:1b`, etc.).
- 🛡️ **Defensive Schema Parsing:** Raw LLM outputs are never trusted directly. SlothSort forces strict JSON schemas, validates categories against predefined whitelists, and sanitizes filenames against OS-level illegal character exploits.

---

## 3. Architecture: The Hybrid Rules-First Engine

Many naive AI file organizers send every single file to an LLM. Asking a 4-billion parameter neural network what `photo.jpg` or `docker.msi` is wastes compute and causes needless delays.

SlothSort uses a **two-tier hybrid pipeline**:

```
                         Messy Directory
                                │
                                ▼
                       ┌─────────────────┐
                       │ 1. Scan Folder  │  Skip subfolders, temp (.crdownload, .tmp),
                       └────────┬────────┘  and files modified < 10 mins ago
                                │
                                ▼
                       ┌─────────────────┐
                       │ 2. Rules Pass   │  .jpg/.png -> Photos, .exe -> Installers,
                       └────────┬────────┘  .zip -> Archives (Matches 50-60% instantly)
                                │
             ┌──────────────────┴──────────────────┐
             ▼                                     ▼
      [Obvious Match]                      [Ambiguous Match]
             │                             (.pdf, .docx, .txt, etc.)
             │                                     │
             │                                     ▼
             │                            ┌─────────────────┐
             │                            │ 3. Text Snippet │  Extract first ~500 chars
             │                            └────────┬────────┘  via pypdf & python-docx
             │                                     │
             │                                     ▼
             │                            ┌─────────────────┐
             │                            │ 4. Gemma 3 (AI) │  Ollama local inference
             │                            └────────┬────────┘  Strict JSON {category, name}
             │                                     │
             └──────────────────┬──────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │ 5. Plan Builder │  Resolve name clashes -> 'file (2).pdf'
                       └────────┬────────┘  Build preview table
                                │
                   ┌────────────┴────────────┐
                   ▼                         ▼
         [Dry-Run Preview]           [--apply Execution]
          Displays table              Moves files + writes
          (0 disk changes)            slothsort_undo.json
```

---

## 4. Safety Non-Negotiables

A file utility that loses, corrupts, or misplaces user data is unacceptable. SlothSort is engineered around **8 ironclad safety rules**:

1. **Dry-Run Default:** Running `slothsort <folder>` only displays the proposed moves. Disk operations require an explicit `--apply` flag.
2. **Never Delete:** Files are only moved via `shutil.move()`. SlothSort never deletes, overwrites, or truncates files.
3. **Audit Trail & Instant Undo:** Every run records `slothsort_undo.json`. Running `slothsort undo` restores all files to their original directories and cleans up empty folders.
4. **Collision Prevention:** If `Bills/invoice.pdf` already exists, SlothSort automatically suffixes the newcomer as `Bills/invoice (2).pdf`.
5. **Top-Level Isolation:** Nested folders are never traversed or altered.
6. **Active Download Protection:** Files with `.crdownload`, `.part`, or `.tmp` extensions are automatically skipped.
7. **Modification Time Guard:** Files modified within the last 10 minutes are ignored by default to prevent touching files still being written or downloaded.
8. **Filename Sanitization:** All names are stripped of Windows-illegal characters (`<>:"/\|?*`), control characters, and trailing spaces or dots.

---

## 5. The "Lazy Payoff" Benchmark

To measure the real-world value of SlothSort, we built a reproducible benchmark suite ([scripts/benchmark.py](file:///c:/Users/ASUS/OneDrive/Documents/SlothSort/scripts/benchmark.py)) evaluated against a test dataset of 35 diverse messy files with ground-truth labels:

| Mode | Files Processed | Correctly Categorized | Accuracy | Time Elapsed | Human Effort Required |
|---|:---:|:---:|:---:|:---:|:---:|
| **Rules Only (`--no-ai`)** | 35 | 19 / 35 | **54.3%** | **0.00s** | 0 seconds |
| **Hybrid (Rules + Gemma 3 4B)** | 35 | 32 / 35 | **91.4%** | **155.89s** | **0 seconds (Hands-free)** |
| **Manual Sorting (Baseline)** | 35 | 35 / 35 | 100.0% | ~120.0s | ~2 minutes of manual dragging |

### Analysis: Rewarding Laziness ("Slow and Steady")
- **The Rules-only mode** is instantaneous (0.00s) and handles 54% of the folder (photos, installers, archives), but fails completely on ambiguous documents.
- **The Hybrid Gemma 3 mode** boosts accuracy to **91.4%**, intelligently deciphering invoices, study lecture notes, resumes, and lease agreements.
- While local CPU inference took ~2.5 minutes, **it requires zero human effort**. You run one command, walk away to make a cup of coffee, and return to a clean, organized folder. That is the essence of **"Slow and Steady"** open-source AI.

---

## 6. Tech Stack

- **Core Language:** Python 3.10+
- **Local AI Engine:** [Ollama](https://ollama.com) running [Google Gemma 3 4B](https://ai.google.dev/gemma)
- **Document Extractors:** `pypdf` (PDF text extraction), `python-docx` (Word document parsing)
- **Terminal Presentation:** `rich` (formatted ASCII tables, panels, and progress indicators)
- **Testing Framework:** `pytest` (33 automated unit tests)

---

## 7. Installation & Setup

### Prerequisites
1. **Python 3.10+** installed.
2. **Ollama** installed from [ollama.com](https://ollama.com).

### Step 1: Pull the Local Gemma Model
```powershell
ollama pull gemma3:4b
```

### Step 2: Clone and Setup Virtual Environment
```powershell
git clone https://github.com/<your-username>/slothsort.git
cd slothsort

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e .
```
*(On Linux/macOS, use `source .venv/bin/activate`)*

---

## 8. CLI Usage

### 1. Dry-Run Preview (Safe — Nothing is moved)
```powershell
python -m slothsort "C:\Users\<you>\Downloads"
```

### 2. Apply Organization
```powershell
python -m slothsort "C:\Users\<you>\Downloads" --apply
```

### 3. Undo the Last Run
```powershell
python -m slothsort undo "C:\Users\<you>\Downloads"
```

### 4. Fast Mode (Rules Only, No AI)
```powershell
python -m slothsort "C:\Users\<you>\Downloads" --no-ai
```

### 5. Custom Model Selection
```powershell
python -m slothsort "C:\Users\<you>\Downloads" --model llama3.2:1b
```

---

## 9. Configuration

Categories, extension rules, and safety thresholds are configured in [categories.json](file:///c:/Users/ASUS/OneDrive/Documents/SlothSort/categories.json):

```json
{
  "categories": [
    "Bills",
    "Study",
    "Career",
    "Photos",
    "Installers",
    "Archives",
    "Documents",
    "Other"
  ],
  "extension_rules": {
    "Photos": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".heic"],
    "Installers": [".exe", ".msi", ".dmg"],
    "Archives": [".zip", ".rar", ".7z", ".tar", ".gz"]
  },
  "skip_extensions": [".crdownload", ".part", ".tmp"],
  "skip_if_modified_within_minutes": 10,
  "default_model": "gemma3:4b"
}
```

---

## 10. Automated Testing

SlothSort includes an exhaustive automated test suite covering filename sanitization, collision avoidance, extension rules, download filtering, PDF/DOCX extractors, AI JSON validation, move operations, and full undo recovery.

To run the full test suite:
```powershell
pytest -v
```

**Results:**
```
tests/test_ai_parsing.py::test_parse_valid_json PASSED                   [  3%]
tests/test_ai_parsing.py::test_parse_markdown_fenced_json PASSED         [  6%]
tests/test_ai_parsing.py::test_parse_unknown_category_fallback PASSED    [  9%]
tests/test_ai_parsing.py::test_parse_broken_json PASSED                  [ 12%]
tests/test_ai_parsing.py::test_parse_strips_extension_from_suggested_name PASSED [ 15%]
tests/test_ai_parsing.py::test_classify_with_ai_mock_client PASSED       [ 18%]
tests/test_extract.py::test_extract_plaintext PASSED                     [ 21%]
tests/test_extract.py::test_extract_docx PASSED                          [ 24%]
tests/test_extract.py::test_extract_pdf PASSED                           [ 27%]
tests/test_extract.py::test_extract_corrupted_file PASSED                [ 30%]
tests/test_extract.py::test_extract_nonexistent_file PASSED              [ 33%]
tests/test_extract.py::test_extract_max_chars_limit PASSED               [ 36%]
tests/test_mover.py::test_execute_plan_and_undo PASSED                   [ 39%]
tests/test_mover.py::test_undo_nonexistent_manifest PASSED               [ 42%]
tests/test_mover.py::test_execute_plan_missing_source PASSED             [ 45%]
tests/test_planner.py::test_build_plan_rules_mode_no_disk_changes PASSED [ 48%]
tests/test_planner.py::test_build_plan_handles_name_collisions PASSED    [ 51%]
tests/test_rules.py::test_get_rule_category_photos PASSED                [ 54%]
tests/test_rules.py::test_get_rule_category_installers PASSED            [ 57%]
tests/test_rules.py::test_get_rule_category_ambiguous_returns_none PASSED [ 60%]
tests/test_rules.py::test_get_rule_category_no_extension PASSED          [ 63%]
tests/test_scanner.py::test_scan_folder_skips_subdirectories PASSED      [ 66%]
tests/test_scanner.py::test_scan_folder_skips_temp_and_partial_downloads PASSED [ 69%]
tests/test_scanner.py::test_scan_folder_skips_undo_manifest_and_hidden PASSED [ 72%]
tests/test_scanner.py::test_scan_folder_recent_filter PASSED             [ 75%]
tests/test_scanner.py::test_scan_folder_invalid_path PASSED              [ 78%]
tests/test_utils.py::test_sanitize_filename_illegal_chars PASSED         [ 81%]
tests/test_utils.py::test_sanitize_filename_trailing_dots_and_spaces PASSED [ 84%]
tests/test_utils.py::test_sanitize_filename_empty PASSED                 [ 87%]
tests/test_utils.py::test_sanitize_filename_max_length PASSED            [ 90%]
tests/test_utils.py::test_get_unique_path PASSED                         [ 93%]
tests/test_utils.py::test_is_recent_file PASSED                          [ 96%]
tests/test_utils.py::test_load_categories_config PASSED                  [100%]

============================= 33 passed in 0.99s ==============================
```

---

## 11. How Judges Can Test Offline

To prove that SlothSort is 100% offline and preserves complete user privacy:

1. **Disconnect from the internet** (turn off Wi-Fi or unplug ethernet).
2. Generate the mock messy dataset:
   ```powershell
   python scripts/make_test_folder.py
   ```
3. Run the dry-run:
   ```powershell
   python -m slothsort test_downloads --ignore-recent
   ```
4. Apply the organization:
   ```powershell
   python -m slothsort test_downloads --ignore-recent --apply
   ```
5. Confirm the tidy folder structure, then reverse everything:
   ```powershell
   python -m slothsort undo test_downloads
   ```
*Notice that zero network calls were made and all Gemma AI classifications completed entirely on device.*

---

## 12. Known Limitations & Roadmap

### Known Limitations
- **Scanned Image PDFs:** PDFs containing only scanned images with no embedded text layer cannot be parsed without OCR; they fall back to filename-based inference.
- **CPU Inference Speed:** On laptops without discrete GPUs, running inference on dozens of documents takes ~2-3 seconds per file.

### Roadmap
- [ ] Lightweight local OCR support (Tesseract) for scanned receipts and screenshots.
- [ ] Background daemon/watcher mode to automatically tidy files as they finish downloading.
- [ ] User memory: Remember user corrections (e.g., "Always put invoices from X into Taxes").
- [ ] Streamlit/Web UI companion for visual one-click approval.

---

## 13. License & Acknowledgments

This project is licensed under the [MIT License](LICENSE).

- **Google Gemma 3:** Built with open-weight intelligence from [Google DeepMind / Gemma](https://ai.google.dev/gemma).
- **Ollama:** Offline local inference powered by [Ollama](https://ollama.com).
- **Hacktoberfest 2026:** Created for the Hacktoberfest Open-Source AI Challenge (Week 3: *Slow and Steady*).