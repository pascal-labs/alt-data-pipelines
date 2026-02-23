# TechStars Founder Data Collection Methodology

## Overview
This document explains the complete data pipeline for finding TechStars company founders and their locations, particularly focusing on Austin, TX founders.

---

## 📊 Data Collection Pipeline

### Phase 1: Company Data (Initial Input)
**Source:** `techstars_companies_clean.csv` (4,042 companies)

**Contains:**
- Company name
- Year
- Location
- Program
- Verticals
- Description
- Website
- LinkedIn
- Crunchbase
- Social media links

---

## 🔍 Phase 2: Founder Discovery

### Method: Tavily AI Search API
**Script:** `run_founder_search_all_locations.py`

**Process:**
1. **Search Query:** `"{company_name} founders"`
   - Uses Tavily AI search (web search API)
   - Returns top 5 results
   - Basic search depth

2. **Founder Name Extraction:**
   - **Priority Source:** Crunchbase results (highest confidence)
   - Pattern matching for:
     - `"Founders Name1, Name2, Name3"`
     - `"Name and Name LastName"` (e.g., "Ben and Moisey Uretsky")
     - `"founder FullName"` or `"co-founder FullName"`
   - Filters out common false positives (company names, titles, etc.)

3. **Result:**
   - Founder names with confidence levels (HIGH/MEDIUM/LOW)
   - Source URLs for verification

**Data Stored:**
- `first_name`
- `last_name`
- `source_url` (where name was found)
- `confidence` level

---

## 📍 Phase 3: LinkedIn URL Discovery

### Method A: Tavily Search for LinkedIn Profiles
**Script:** `run_founder_search_all_locations.py` (function: `get_founder_location()`)

**Process:**
1. **Search Query:** `"{founder_name}" LinkedIn profile`
2. **Filter Results:** Only URLs containing `linkedin.com/in/`
3. **Extract Location:** Parse location from title/content using patterns:
   - `Location: [City, State, Country]`
   - `Based in [Location]`
   - `Lives in [Location]`
   - City/State patterns: `Austin, TX` or `Austin, Texas, United States`

**Limitations:**
- Tavily only returns snippets/previews from LinkedIn
- Cannot access full LinkedIn profile data
- Location data is often incomplete or missing
- Only ~260 profiles got location data this way

**Result Status:**
- Profiles with location → stored directly
- Profiles found but no location → marked as `PENDING_BRIGHTDATA`
- No LinkedIn found → marked as `NO_LOCATION_FOUND`

---

### Method B: Bright Data LinkedIn Scraping API
**Script:** `process_pending_brightdata.py`

**Purpose:** Enrich the 5,747 profiles marked as `PENDING_BRIGHTDATA`

**Process:**
1. **Batch Submission:**
   - Send LinkedIn URLs to Bright Data API
   - Method: `brightdata_client.scrape_linkedin.profiles(urls)`
   - Returns `snapshot_id` for polling

2. **Snapshot Polling:**
   - Poll every 30 seconds (max 60 attempts = 30 min)
   - Download results: `brightdata_client.download_snapshot(snapshot_id)`

3. **Data Extraction:**
   - Bright Data returns 3 location fields:
     - `location`: Short city name (e.g., "Austin")
     - `city`: Full location string (e.g., "Austin, Texas, United States")
     - `country_code`: Country code (e.g., "US")
   - Priority: `city` → `location` → `country_code`

4. **URL Matching:**
   - LinkedIn redirects to country-specific domains (e.g., `cn.linkedin.com`, `uk.linkedin.com`)
   - Match using `input.url` field (original URL) not `url` field (redirected URL)

**Success Rate:**
- 5,474 profiles processed
- 5,386 profiles with location data (98.4% success)
- 88 profiles with no location (private/deleted accounts)

**Result:**
- Updated 5,633 founder locations total (includes 260 from Tavily + 5,386 from Bright Data, with some overlap)
- 124 Austin founders identified

---

## 🎯 Austin Detection Logic

### Keyword Matching
Locations are checked for Austin-area keywords (case-insensitive):
- Austin
- Round Rock
- Georgetown
- Cedar Park
- Pflugerville
- Leander
- Kyle
- Buda
- Lakeway
- Bee Cave
- Dripping Springs
- Hutto
- Manor
- ATX (abbreviation)

**Location Examples:**
- ✅ "Austin, Texas, United States"
- ✅ "Austin, Texas Metropolitan Area"
- ✅ "Greater Austin Metropolitan Area"
- ✅ "Round Rock, Texas, United States"
- ❌ "Rochester-Austin, Minnesota Area" (false positive - different Austin)

---

## 📁 Final Data Structure

### Checkpoint File: `hybrid_final_checkpoint.json`
```json
{
  "company_index": 0,
  "company_name": "DigitalOcean",
  "founders": [
    {
      "first_name": "Ben",
      "last_name": "Uretsky",
      "linkedin_url": "https://www.linkedin.com/in/benuretsky",
      "location": "New York, New York, United States",
      "is_austin": false
    }
  ]
}
```

### Output CSVs

#### 1. Expanded Format (One Row Per Founder)
**File:** `techstars_companies_expanded_by_founder_FIXED.csv` (7,642 rows)

**Structure:**
- All company fields (name, year, location, etc.)
- Founder fields:
  - `founder_first_name`
  - `founder_last_name`
  - `founder_full_name`
  - `founder_linkedin_url`
  - `founder_location`
  - `founder_is_austin` (TRUE/FALSE)

**Use Case:** Filter/analyze by individual founders

#### 2. Aggregated Format (One Row Per Company)
**File:** `techstars_companies_with_founders_FIXED.csv` (4,042 rows)

**Structure:**
- All company fields
- Aggregated founder data:
  - `total_founders` (count)
  - `austin_founders` (count)
  - `has_austin_founder` (TRUE/FALSE)
  - `founder_names` (pipe-separated: "Name1 | Name2 | Name3")
  - `founder_locations` (pipe-separated)
  - `founder_linkedin_urls` (pipe-separated)

**Use Case:** Company-level analysis

#### 3. Austin-Only Versions
- `techstars_companies_expanded_AUSTIN_FOUNDERS_ONLY_FIXED.csv` (124 rows)
- `techstars_companies_AUSTIN_FOUNDERS_ONLY_FIXED.csv` (96 companies)

---

## 🔢 Final Statistics

### Coverage
- **Total Companies:** 4,042
- **Total Founders Found:** 7,642
- **Founders with LinkedIn URLs:** 6,002 (78.5%)
- **Founders with Locations:** 5,633 (73.7%)

### Austin Founders
- **Austin Founders:** 124 individuals
- **Companies with Austin Founders:** 96 companies
- **Austin Founder Rate:** 1.6% of all founders

### Data Quality
- **LinkedIn Discovery Rate:** 78.5%
- **Location Enrichment Rate:** 98.4% (of those with LinkedIn URLs)
- **Overall Location Success:** 73.7% of all founders

---

## 🔧 Technical Details

### API Services Used

1. **Tavily AI Search**
   - API Key: `REDACTED`
   - Rate Limiting: Random delays 0.5-3s between requests
   - Cost: Pay-per-search
   - Success Rate: ~85% for finding founders

2. **Bright Data LinkedIn Scraper**
   - API Key: `REDACTED`
   - Batch Processing: Up to 5,747 URLs in one request
   - Polling: 30s intervals, 30min max timeout
   - Success Rate: 98.4% for getting locations

### Key Scripts

1. **`run_founder_search_all_locations.py`**
   - Main discovery script
   - Uses Tavily for founder names + LinkedIn URLs
   - Checkpoint-based resumable processing

2. **`process_pending_brightdata.py`**
   - Enrichment script for missing locations
   - Bright Data API integration
   - Batch processing with retry logic

3. **`fix_layering.py`**
   - Merges founder data back into company CSV
   - Fixes pandas index alignment issues
   - Creates multiple output formats

### Checkpoint System
- **File:** `hybrid_final_checkpoint.json`
- **Features:**
  - Saves after every company processed
  - Resumable from any point
  - Tracks status: SUCCESS, PENDING_BRIGHTDATA, NO_LOCATION_FOUND
  - Incremental updates prevent data loss

---

## 🚨 Known Issues & Fixes

### Issue 1: Index Misalignment
**Problem:** CSV row numbers ≠ pandas DataFrame indexes
- CSV row 1 = header
- CSV row 2 = DataFrame index 0
- Original layering script used `row_num` starting at 1

**Fix:** Use pandas `.iterrows()` to get proper DataFrame indexes (0-based)

### Issue 2: Bright Data Field Parsing
**Problem:** Script only checked `city` and `country_code`, missed `location` field

**Fix:** Check all three fields in priority order: `city` → `location` → `country_code`

### Issue 3: LinkedIn URL Matching
**Problem:** Bright Data redirects to country-specific domains
- Input: `www.linkedin.com/in/user`
- Output: `uk.linkedin.com/in/user`

**Fix:** Match on `input.url` field instead of `url` field

---

## 📈 Success Metrics

✅ **Founder Discovery:** 7,642 founders from 4,042 companies (avg 1.9 founders/company)

✅ **LinkedIn Coverage:** 78.5% of founders have LinkedIn URLs

✅ **Location Data:** 73.7% of all founders have location data

✅ **Austin Identification:** 124 Austin-based founders across 96 companies

✅ **Data Quality:** 98.4% success rate on Bright Data enrichment

---

## 🔄 Reproducibility

To reproduce this dataset:

1. Start with `techstars_companies_clean.csv`
2. Run: `python3 run_founder_search_all_locations.py --batch 4042`
3. Run: `python3 process_pending_brightdata.py`
4. Run: `python3 fix_layering.py`

All scripts include checkpoint/resume functionality for reliability.

---

**Last Updated:** October 14, 2025
**Data Collection Period:** October 2-14, 2025
