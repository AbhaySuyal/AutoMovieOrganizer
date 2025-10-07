import os, re, shutil, time, requests, socket
import tmdbsimple as tmdb
from pymediainfo import MediaInfo
from rapidfuzz import fuzz, process

# === CONFIGURATION ===
MOVIE_DIR = r"E:\Entertainment\Movies"
SORTED_DIR = os.path.join(MOVIE_DIR, "movie_sorted")
tmdb.API_KEY = "YOUR API KEY HERE"   # Replace with your TMDb v3 API key

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".wmv"}
SUB_EXTS   = {".srt", ".sub"}

# Common scene/encoding junk, tech specs, and labels to strip
JUNK_WORDS = [
    # Resolutions / sources / rip types
    "2160p","1080p","720p","480p","4k","uhd","hdr","hdr10","dolby vision","dv","sdr",
    "bluray","blu-ray","bdrip","brrip","brrip","hdrip","webrip","web-rip","webdl","web-dl","web",
    "dvdscr","dvdscreener","ts","cam","remux","rip","remastered","criterion","imax",
    # Codecs / bit-depth / channels
    "x264","x265","h264","h265","hevc","av1","10bit","8bit","dts","truehd","atmos","eac3","aac","ac3","mp3",
    "dd","dd+","ddp","6ch","2ch","5.1","7.1",
    # Scene flags / language tags
    "proper","repack","limited","extended","unrated","director's cut","directors cut","dual audio","multi","subbed","dubbed",
    "eng","english","hin","hindi","kor","korean","jpn","japanese","spa","spanish",
    # Misc banner tokens often embedded
    "sample","nfo","rip","hc","cam"
]

# Release groups, sites, and common tag sources to strip
RELEASE_GROUPS = [
    "YIFY","YTS","RARBG","EVO","ETRG","PSA","MkvCage","Ganool","TGx","HEVCBay","Esub","HDHub4u",
    "KatMovieHD","1337x","Skytorrents","LimeTorrents","TorrentGalaxy","Peliculas","TamilRockers","DocuWiki",
    "HDElite","SceneTime","XVID","HDCAM","CAMRip","NF","AMZN","Netflix","Prime","Disney","Hulu"
]

# Site/banner patterns to strip (www.domain.tld forms)
SITE_PATTERN = r"(www\.[A-Za-z0-9\-\_]+\.(com|net|org|tw|in|ru|cc))"

INVALID_CHARS = r'[<>:"/\\|?*]'

# Known franchise keywords where collection fallback helps
FRANCHISE_HINTS = [
    "harry potter","hobbit","lord of the rings","hunger games","fast and furious","star wars",
    "jurassic park","jurassic world","pirates of the caribbean","mission impossible","rocky","creed",
    "transformers","toy story","mad max","the godfather","terminator","riddick","bourne"
]

# --- Force IPv4 (avoid IPv6 issues) ---
import requests.packages.urllib3.util.connection as urllib3_cn
def allowed_gai_family():
    return socket.AF_INET
urllib3_cn.allowed_gai_family = allowed_gai_family

# --- Networking setup (persistent session with retries) ---
session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=5)
session.mount("https://", adapter)

def safe_filename(name):
    """Remove Windows-invalid characters"""
    return re.sub(INVALID_CHARS, "", name)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)

def copy_with_rename(src, dest_dir, new_basename, ext):
    ensure_dir(dest_dir)
    new_basename = safe_filename(new_basename)
    dest_path = os.path.join(dest_dir, f"{new_basename}{ext}")
    if not os.path.exists(dest_path):
        print(f"➡️ Copying: {src} → {dest_path}")
        shutil.copy(src, dest_path)
    else:
        print(f"⚠️ Already exists: {dest_path}")
    return dest_path

def get_embedded_title(file_path):
    """Try to extract embedded title metadata from video"""
    try:
        media_info = MediaInfo.parse(file_path)
        for track in media_info.tracks:
            if track.track_type == "General" and track.title:
                return track.title
    except Exception as e:
        print(f"⚠️ Could not read embedded metadata for {file_path}: {e}")
    return None

def base_clean(text):
    """Normalize separators and spacing"""
    t = text.replace("|", " ").replace(".", " ").replace("_", " ").replace("-", " ")
    t = re.sub(r"\s+", " ", t).strip()
    return t

def aggressive_strip(text):
    """Strip release groups, site banners, junk words, tech specs"""
    t = text
    # Remove site banners
    t = re.sub(SITE_PATTERN, "", t, flags=re.IGNORECASE)
    # Remove release groups
    for rg in RELEASE_GROUPS:
        t = re.sub(rf"\b{re.escape(rg)}\b", "", t, flags=re.IGNORECASE)
    # Remove junk words/tech specs
    for junk in JUNK_WORDS:
        t = re.sub(rf"\b{re.escape(junk)}\b", "", t, flags=re.IGNORECASE)
    # Remove repeated dots or separators remnants
    t = base_clean(t)
    # Remove extra commas and parentheses artifacts like "(EXTENDED)" remnants
    t = re.sub(r"\s*\(\s*\)", "", t)
    return t.strip()

def normalize_query(raw):
    """Return (clean_query, year, franchise_hint)"""
    # First, normalize separators
    text = base_clean(raw)
    # Extract year first (to preserve it before stripping)
    year_match = re.search(r"(19|20)\d{2}", text)
    year = year_match.group(0) if year_match else None
    # Aggressively strip junk
    text = aggressive_strip(text)
    # Remove year from query phrase (TMDb has separate year param)
    if year:
        text = re.sub(rf"\b{year}\b", "", text).strip()
    # Collapse spaces and trim
    text = re.sub(r"\s+", " ", text).strip()
    # Detect franchise hint
    low = text.lower()
    hint = None
    for h in FRANCHISE_HINTS:
        if h in low:
            hint = h
            break
    return text, year, hint

def fuzzy_pick(query, results, prefer_year=None):
    """Pick best TMDb result by fuzzy match; bias to same year if provided"""
    if not results:
        return None
    titles = []
    for r in results:
        # Prefer official title; fallback to original_title
        title = r.get("title") or r.get("original_title") or ""
        titles.append(title)
    # Use fuzzy WRatio for resilience
    best = process.extractOne(query, titles, scorer=fuzz.WRatio)
    chosen_idx = best[2] if best and best[1] >= 60 else 0
    chosen = results[chosen_idx]
    # Year bias: if provided and there are multiple with close scores, prefer matching year
    if prefer_year:
        y_matches = [i for i, r in enumerate(results) if (r.get("release_date") or "")[:4] == prefer_year]
        if y_matches:
            # If the chosen doesn't match the year but a candidate does, switch
            if (chosen.get("release_date") or "")[:4] != prefer_year:
                chosen = results[y_matches[0]]
    return chosen

def tmdb_details(movie_id):
    """Get full details for a movie id"""
    resp = session.get(
        f"https://api.themoviedb.org/3/movie/{movie_id}",
        params={"api_key": tmdb.API_KEY},
        timeout=10
    )
    resp.raise_for_status()
    return resp.json()

def tmdb_collection_parts_by_name(name):
    """Search collection by name and return parts"""
    resp = session.get(
        "https://api.themoviedb.org/3/search/collection",
        params={"api_key": tmdb.API_KEY, "query": name},
        timeout=10
    )
    resp.raise_for_status()
    coll_results = resp.json().get("results", [])
    if not coll_results:
        return []
    coll_id = coll_results[0]["id"]
    info = session.get(
        f"https://api.themoviedb.org/3/collection/{coll_id}",
        params={"api_key": tmdb.API_KEY},
        timeout=10
    ).json()
    return info.get("parts", [])

def tmdb_lookup(query, max_retries=6):
    """Search TMDb with retries + aggressive normalization + fuzzy matching + year bias + collection fallback"""
    clean_query, year, hint = normalize_query(query)
    delay = 2
    for attempt in range(max_retries):
        try:
            # 1) Primary movie search
            params = {"api_key": tmdb.API_KEY, "query": clean_query}
            if year:
                params["year"] = year
            response = session.get("https://api.themoviedb.org/3/search/movie", params=params, timeout=10)
            response.raise_for_status()
            results = response.json().get("results", [])
            chosen = fuzzy_pick(clean_query, results, prefer_year=year)

            # 2) If movie search failed and we have a franchise hint, try collection fallback
            if not chosen and hint:
                # Use the hint or first two words as collection query
                coll_query = hint if hint else " ".join(clean_query.split()[:2])
                parts = tmdb_collection_parts_by_name(coll_query)
                if parts:
                    # Fuzzy across parts by title, bias by year
                    part_titles = [p.get("title") or p.get("original_title") or "" for p in parts]
                    bm = process.extractOne(clean_query, part_titles, scorer=fuzz.WRatio)
                    p_idx = bm[2] if bm and bm[1] >= 60 else 0
                    # Year bias
                    if year:
                        y_matches = [i for i, p in enumerate(parts) if (p.get("release_date") or "")[:4] == year]
                        if y_matches and (parts[p_idx].get("release_date") or "")[:4] != year:
                            p_idx = y_matches[0]
                    # Simulate chosen payload structure (id/title/release_date)
                    chosen = {"id": parts[p_idx]["id"], "title": parts[p_idx].get("title"),
                              "release_date": parts[p_idx].get("release_date")}

            if not chosen:
                return None

            # Get full details for chosen
            details = tmdb_details(chosen["id"])

            collection = details.get("belongs_to_collection")
            collection_name = collection["name"] if collection else None

            year_val = (details.get("release_date") or "")[:4]
            if not year_val.isdigit():
                year_val = "Unknown"

            return {
                "title": details.get("title") or details.get("original_title") or clean_query,
                "language": (details.get("original_language") or "Unknown").capitalize(),
                "year": year_val,
                "genres": [g["name"] for g in details.get("genres", [])] or ["Unknown"],
                "collection": collection_name
            }

        except requests.exceptions.RequestException as e:
            print(f"🌐 TMDb error for '{clean_query}' (attempt {attempt+1}/{max_retries}): {e}")
            time.sleep(delay)
            delay *= 2  # exponential backoff

    print(f"❌ All retries failed for '{clean_query}', falling back to Unknown")
    return None

def is_related_subtitle(video_stem, sub_stem):
    # Compare cleaned stems
    v = aggressive_strip(video_stem).lower()
    s = aggressive_strip(sub_stem).lower()
    return v and v in s

def organize_movies():
    print(f"📂 Scanning recursively: {MOVIE_DIR}")
    ensure_dir(SORTED_DIR)

    for root, _, files in os.walk(MOVIE_DIR):
        # Skip already sorted directory
        try:
            if os.path.commonpath([root, SORTED_DIR]) == SORTED_DIR:
                continue
        except ValueError:
            pass

        subs_in_root = [f for f in files if os.path.splitext(f)[1].lower() in SUB_EXTS]

        for f in files:
            ext = os.path.splitext(f)[1].lower()
            if ext not in VIDEO_EXTS:
                continue

            src_path = os.path.join(root, f)
            stem = os.path.splitext(f)[0]

            # Step 1: Try embedded metadata; if present, clean aggressively; else use filename and clean
            embedded_title = get_embedded_title(src_path)
            if embedded_title:
                query_raw = embedded_title
                print(f"🔎 Using embedded title: {embedded_title}")
            else:
                query_raw = stem
                print(f"🔎 Using filename fallback: {stem}")

            # Step 2: Lookup TMDb with normalization + fuzzy + collection fallback + strong retry
            meta = tmdb_lookup(query_raw) or {
                "title": aggressive_strip(query_raw), "language": "Unknown", "year": "Unknown",
                "genres": ["Unknown"], "collection": None
            }

            chosen_genre = sorted(meta["genres"])[0]
            if meta["collection"]:
                dest_dir = os.path.join(SORTED_DIR, meta["language"], chosen_genre, meta["collection"])
            else:
                dest_dir = os.path.join(SORTED_DIR, meta["language"], chosen_genre)

            new_basename = f"{meta['title']} ({meta['year']})"
            copy_with_rename(src_path, dest_dir, new_basename, ext)

            # Step 3: Copy subtitles next to the movie
            for sub_file in subs_in_root:
                sub_ext = os.path.splitext(sub_file)[1].lower()
                sub_stem = os.path.splitext(sub_file)[0]
                if is_related_subtitle(stem, sub_stem):
                    sub_src = os.path.join(root, sub_file)
                    copy_with_rename(sub_src, dest_dir, new_basename, sub_ext)

            # Step 4: Rate limit friendliness
            time.sleep(0.5)

    print("✅ Metadata-based sorting with aggressive cleanup, fuzzy matching, and collection fallback complete!")

if __name__ == "__main__":
    organize_movies()
