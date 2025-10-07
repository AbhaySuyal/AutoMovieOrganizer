# AutoMovieOrganizer

![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![TMDb](https://img.shields.io/badge/TMDb-API-blue)
![OMDb](https://img.shields.io/badge/OMDb-API-yellow)
![RapidAPI](https://img.shields.io/badge/RapidAPI-Cinemalytics-orange)

**AutoMovieOrganizer** is a metadata-first movie organizer that scans your movie library, cleans messy filenames, and organizes movies and subtitles into a structured directory. Works with Bollywood & Hollywood, old and new releases, including classics.

---

## Table of Contents

- [Features](#features)  
- [Demo](#demo)  
- [Requirements](#requirements)  
- [Installation](#installation)  
- [Usage](#usage)  
- [Configuration](#configuration)  
- [Advanced Settings](#advanced-settings)  
- [Troubleshooting](#troubleshooting)  
- [Notes](#notes)  
- [License](#license)  

---

## Features

- **Metadata-first:** Reads embedded metadata when available  
- **Aggressive filename normalization**: Removes release groups, site banners, tech specs  
- **Year-biased fuzzy matching** with [RapidFuzz](https://github.com/maxbachmann/RapidFuzz)  
- **Collection fallback:** Automatically groups franchises (Harry Potter, Lord of the Rings)  
- **Multi-provider lookup:** TMDb → OMDb → Cinemalytics (optional for Bollywood)  
- **Copy, not move:** Originals stay intact; subtitles preserved  
- **Local JSON cache** for faster subsequent runs  
- **Structured folders:** Language / Genre / Collection  

---


## Requirements

- **Python 3.10+**  
- **Python packages:**
```bash
pip install pymediainfo requests tmdbsimple rapidfuzz
```  
- **MediaInfo:** [Install here](https://mediaarea.net/en/MediaInfo) and ensure binary is on PATH  
- **API Keys:**  
  - TMDb (required)  
  - OMDb (recommended)  
  - RapidAPI (optional, for Cinemalytics/Bollywood)  

---

## Installation

1. Clone the repository  
2. Copy `moviesort.py` to your working folder  
3. Install required packages and MediaInfo  
4. Configure API keys and folders (see [Configuration](#configuration))  

---

## Usage

```bash
python moviesort.py
```

**Example output folder structure:**

```
movie_sorted/
├─ English/
│  ├─ Adventure/
│  │  └─ Harry Potter Collection/
│  │     ├─ Harry Potter and the Sorcerer’s Stone (2001).mkv
│  │     └─ Harry Potter and the Chamber of Secrets (2002).mp4
│  └─ Action/
│     └─ Sherlock Holmes (2009).mp4
└─ Hindi/
   └─ Drama/
      └─ 3 Idiots (2009).mkv
```

---

## Configuration

<details>
<summary>Click to expand</summary>

Edit the top configuration block in `moviesort.py`:

```python
MOVIE_DIR      # Path to raw movie folder
SORTED_DIR     # Destination folder (optional)
tmdb.API_KEY   # TMDb API key
OMDB_API_KEY   # Optional
RAPIDAPI_KEY   # Optional for Bollywood
```

Optional lists to customize:

- `VIDEO_EXTS` / `SUB_EXTS` — supported extensions  
- `RELEASE_GROUPS` — release tags to remove  
- `JUNK_WORDS` — extra junk words in filenames
</details>

---

## Advanced Settings

<details>
<summary>Click to expand</summary>

- **Retry & backoff:** Exponential retry for API failures  
- **Force IPv4:** Reduces network errors in some environments  
- **Year extraction:** Used for disambiguation in fuzzy matching  
- **Cache:** `metadata_cache.json` speeds up repeated runs  
- **Subtitle pairing:** Cleans video stems for substring matching  
- **Collection fallback:** Automatically detects movie franchises  

You can extend the script with:

- Additional providers (offline IMDb datasets)  
- Custom folder hierarchies  
- Local caching strategies
</details>

---

## Troubleshooting

<details>
<summary>Click to expand</summary>

**Max retries / TLS errors:**  

- Upgrade packages:
```bash
pip install --upgrade requests urllib3 certifi
```  
- Test connectivity to TMDb  
- Switch DNS or use a VPN if blocked

**Poor matches:**  

- Add common release groups to `RELEASE_GROUPS`  
- Expand `JUNK_WORDS` for your library

**Subtitles not paired:**  

- Ensure subtitle filenames match cleaned video stems
</details>

---

## Notes

- Provider chain: TMDb → OMDb → Cinemalytics  
- Year extraction helps disambiguate movies with similar titles  
- Cache avoids repeated API calls  
- Works for Bollywood & Hollywood, classics and recent releases  

---

