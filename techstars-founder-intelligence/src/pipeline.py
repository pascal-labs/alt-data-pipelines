#!/usr/bin/env python3
"""
COMPLETE FOUNDER ENRICHMENT PIPELINE V2
FIXED: Don't use site: operator, just search and filter LinkedIn URLs
"""
import json
import time
import re
import pandas as pd
import csv
from tavily import TavilyClient
from brightdata import bdclient
from concurrent.futures import ThreadPoolExecutor, as_completed

# API Keys
# Import from config
from config import TAVILY_API_KEY, BRIGHTDATA_API_KEY
CHECKPOINT_FILE = "data/checkpoints/hybrid_final_checkpoint.json"
COMPANIES_CSV = "data/input/techstars_companies_clean.csv"

tavily = TavilyClient(api_key=TAVILY_API_KEY)

def load_checkpoint():
    with open(CHECKPOINT_FILE, 'r') as f:
        return json.load(f)

def save_checkpoint(checkpoint):
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

# ============================================================================
# STEP 1: FIND MISSING LINKEDIN URLS WITH VERIFICATION
# ============================================================================

def extract_linkedin_name(url):
    """Extract the name portion from LinkedIn URL"""
    match = re.search(r'linkedin\.com/in/([^/?]+)', url)
    if match:
        profile_id = match.group(1)
        clean_id = re.sub(r'-\d+$', '', profile_id)
        return clean_id.lower()
    return None

def verify_name_match(founder_name, linkedin_url):
    """Verify that LinkedIn URL matches founder name"""
    linkedin_id = extract_linkedin_name(linkedin_url)
    if not linkedin_id:
        return False

    founder_lower = founder_name.lower()
    linkedin_lower = linkedin_id.lower()

    expected_with_dash = founder_lower.replace(' ', '-')
    expected_no_space = founder_lower.replace(' ', '')

    if expected_with_dash in linkedin_lower or expected_no_space in linkedin_lower:
        return True

    expected_parts = set(founder_lower.split())
    linkedin_parts = set(linkedin_lower.replace('-', ' ').split())

    if len(expected_parts) >= 2 and len(expected_parts & linkedin_parts) >= 2:
        return True

    first_name = founder_lower.split()[0] if founder_lower.split() else ''
    last_name = founder_lower.split()[-1] if len(founder_lower.split()) > 1 else ''

    if first_name and last_name:
        patterns = [
            first_name + last_name,
            last_name + first_name,
            first_name[0] + last_name,
        ]
        linkedin_letters = linkedin_lower.replace('-', '')
        for pattern in patterns:
            if pattern in linkedin_letters:
                return True

    return False

def find_linkedin_url(founder_name, company_name):
    """Find LinkedIn URL with name verification - NO site: operator"""
    # FIXED: Don't use site:linkedin.com, just search for the person + LinkedIn
    query = f'"{founder_name}" "{company_name}" LinkedIn'

    try:
        results = tavily.search(query=query, max_results=10, search_depth="basic")

        # Filter for LinkedIn URLs from the results
        for result in results.get('results', []):
            url = result.get('url', '')

            # Must be a LinkedIn profile
            if 'linkedin.com/in/' not in url:
                continue

            clean_url = url.split('?')[0]
            if verify_name_match(founder_name, clean_url):
                return ('verified', clean_url)

        # Fallback: search without company name
        fallback_query = f'"{founder_name}" LinkedIn profile'
        results = tavily.search(query=fallback_query, max_results=10, search_depth="basic")

        for result in results.get('results', []):
            url = result.get('url', '')
            if 'linkedin.com/in/' not in url:
                continue

            clean_url = url.split('?')[0]
            if verify_name_match(founder_name, clean_url):
                return ('verified', clean_url)

        return ('not_verified', None)

    except Exception as e:
        print(f"      ❌ ERROR searching {founder_name}: {type(e).__name__}: {str(e)}")
        return ('error', None)

def process_founder_search(founder_info):
    status, linkedin_url = find_linkedin_url(
        founder_info['founder_name'],
        founder_info['company_name']
    )
    return (founder_info, status, linkedin_url)

def find_missing_linkedin_urls():
    """STEP 1: Find LinkedIn URLs for founders without them"""
    print(f"\n{'='*70}")
    print(f"📍 STEP 1: FINDING MISSING LINKEDIN URLS")
    print(f"{'='*70}\n")

    checkpoint = load_checkpoint()
    missing = []

    for result in checkpoint['results']:
        for founder_idx, founder in enumerate(result['founders']):
            linkedin_url = founder.get('linkedin_url', '')
            first_name = founder.get('first_name', '')
            last_name = founder.get('last_name', '')
            full_name = f"{first_name} {last_name}".strip()

            if not full_name or linkedin_url:
                continue

            missing.append({
                'company_index': result['company_index'],
                'company_name': result['company_name'],
                'founder_index': founder_idx,
                'founder_name': full_name
            })

    if not missing:
        print("✅ All founders already have LinkedIn URLs!\n")
        return 0

    print(f"📊 Found {len(missing):,} founders without LinkedIn URLs")
    print(f"⚡ Processing in parallel with name verification...")
    print(f"🔧 Using improved search (no site: operator)\n")

    chunk_size = 50
    total_verified = 0

    for chunk_start in range(0, len(missing), chunk_size):
        chunk = missing[chunk_start:chunk_start + chunk_size]

        print(f"🔄 Chunk {chunk_start//chunk_size + 1}/{(len(missing)-1)//chunk_size + 1} ({len(chunk)} founders)...")

        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(process_founder_search, f) for f in chunk]
            results = [future.result() for future in as_completed(futures)]

        verified_count = 0
        for founder_info, status, linkedin_url in results:
            if status == 'verified':
                company_idx = founder_info['company_index']
                founder_idx = founder_info['founder_index']

                for result in checkpoint['results']:
                    if result['company_index'] == company_idx:
                        if founder_idx < len(result['founders']):
                            result['founders'][founder_idx]['linkedin_url'] = linkedin_url
                            result['founders'][founder_idx]['location'] = 'PENDING_BRIGHTDATA'
                            verified_count += 1
                            print(f"   ✅ {founder_info['founder_name']}: {linkedin_url}")
                        break

        total_verified += verified_count
        save_checkpoint(checkpoint)
        print(f"   📊 Verified: {verified_count}, Not found: {len(chunk) - verified_count}")
        print(f"   💾 Saved\n")

        if chunk_start + chunk_size < len(missing):
            time.sleep(3)

    print(f"✅ Found {total_verified:,} new verified LinkedIn URLs\n")
    return total_verified

# ============================================================================
# STEP 2: ENRICH WITH BRIGHT DATA
# ============================================================================

def enrich_with_brightdata():
    """STEP 2: Get locations from Bright Data"""
    print(f"\n{'='*70}")
    print(f"📍 STEP 2: ENRICHING WITH BRIGHT DATA")
    print(f"{'='*70}\n")

    checkpoint = load_checkpoint()
    pending = []

    for result in checkpoint['results']:
        for founder_idx, founder in enumerate(result['founders']):
            if founder.get('location') == 'PENDING_BRIGHTDATA' and founder.get('linkedin_url'):
                pending.append({
                    'founder_name': f"{founder.get('first_name', '')} {founder.get('last_name', '')}".strip(),
                    'linkedin_url': founder.get('linkedin_url'),
                    'company_index': result['company_index'],
                    'founder_index': founder_idx
                })

    if not pending:
        print("✅ No pending profiles to enrich!\n")
        return 0

    print(f"📊 Found {len(pending):,} profiles to enrich")
    print(f"🚀 Sending all to Bright Data in one batch...\n")

    brightdata_client = bdclient(api_token=BRIGHTDATA_API_KEY)
    linkedin_urls = [p['linkedin_url'] for p in pending]

    try:
        response = brightdata_client.scrape_linkedin.profiles(linkedin_urls)
        snapshot_id = response.get('snapshot_id')
        print(f"✅ Snapshot created: {snapshot_id}")
        print(f"⏳ Polling for results (max 30 min)...\n")

        for attempt in range(60):
            time.sleep(30)

            try:
                results = brightdata_client.download_snapshot(snapshot_id)

                if results and isinstance(results, list) and len(results) > 0:
                    print(f"✅ Downloaded {len(results)} profiles!\n")

                    updated_count = 0
                    for profile in results:
                        # Use input.url for matching
                        linkedin_url = profile.get('input', {}).get('url', '')
                        location_field = profile.get('location', '')
                        city = profile.get('city', '')
                        country_code = profile.get('country_code', '')

                        if city:
                            location = city
                        elif location_field:
                            location = location_field
                        elif country_code:
                            location = country_code
                        else:
                            continue

                        for pending_info in pending:
                            if pending_info['linkedin_url'] == linkedin_url:
                                company_idx = pending_info['company_index']
                                founder_idx = pending_info['founder_index']

                                for result in checkpoint['results']:
                                    if result['company_index'] == company_idx:
                                        if founder_idx < len(result['founders']):
                                            result['founders'][founder_idx]['location'] = location
                                            is_austin = any(kw in location.lower() for kw in ['austin', 'atx'])
                                            result['founders'][founder_idx]['is_austin'] = is_austin
                                            updated_count += 1
                                        break

                    save_checkpoint(checkpoint)
                    print(f"✅ Updated {updated_count:,} locations")
                    print(f"💾 Checkpoint saved\n")
                    return updated_count

                else:
                    print(f"⏳ Attempt {attempt + 1}/60...")

            except Exception as e:
                print(f"⚠️  Poll error: {e}")
                continue

        print("⚠️  Timeout after 30 minutes\n")
        return 0

    except Exception as e:
        print(f"❌ Bright Data error: {e}\n")
        return 0

# ============================================================================
# STEP 3: REGENERATE CSVS
# ============================================================================

def regenerate_csvs():
    """STEP 3: Create final CSV outputs"""
    print(f"\n{'='*70}")
    print(f"📍 STEP 3: REGENERATING CSV FILES")
    print(f"{'='*70}\n")

    checkpoint = load_checkpoint()
    df = pd.read_csv(COMPANIES_CSV)

    index_to_founders = {}
    for result in checkpoint['results']:
        index_to_founders[result['company_index']] = result.get('founders', [])

    expanded_rows = []
    austin_count = 0

    for idx, company_row in df.iterrows():
        founders = index_to_founders.get(idx, [])

        if not founders:
            row = company_row.to_dict()
            row.update({
                'founder_first_name': '',
                'founder_last_name': '',
                'founder_full_name': '',
                'founder_linkedin_url': '',
                'founder_location': '',
                'founder_is_austin': 'FALSE'
            })
            expanded_rows.append(row)
        else:
            for founder in founders:
                row = company_row.to_dict()
                row.update({
                    'founder_first_name': founder.get('first_name', ''),
                    'founder_last_name': founder.get('last_name', ''),
                    'founder_full_name': f"{founder.get('first_name', '')} {founder.get('last_name', '')}".strip(),
                    'founder_linkedin_url': founder.get('linkedin_url', ''),
                    'founder_location': founder.get('location', ''),
                    'founder_is_austin': 'TRUE' if founder.get('is_austin', False) else 'FALSE'
                })
                expanded_rows.append(row)

                if founder.get('is_austin', False):
                    austin_count += 1

    fieldnames = list(df.columns) + [
        'founder_first_name', 'founder_last_name', 'founder_full_name',
        'founder_linkedin_url', 'founder_location', 'founder_is_austin'
    ]

    expanded_csv = "techstars_companies_expanded_by_founder_ENRICHED.csv"
    with open(expanded_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(expanded_rows)

    print(f"✅ Expanded: {expanded_csv} ({len(expanded_rows):,} rows)")

    austin_only_expanded = "techstars_companies_expanded_AUSTIN_FOUNDERS_ONLY_ENRICHED.csv"
    austin_rows = [row for row in expanded_rows if row['founder_is_austin'] == 'TRUE']
    with open(austin_only_expanded, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(austin_rows)

    print(f"✅ Austin expanded: {austin_only_expanded} ({len(austin_rows):,} rows)")

    # Aggregated
    agg_rows = []
    for idx, company_row in df.iterrows():
        founders = index_to_founders.get(idx, [])
        row = company_row.to_dict()
        row.update({
            'total_founders': len(founders),
            'austin_founders': sum(1 for f in founders if f.get('is_austin', False)),
            'has_austin_founder': 'TRUE' if any(f.get('is_austin', False) for f in founders) else 'FALSE',
            'founder_names': ' | '.join(f"{f.get('first_name', '')} {f.get('last_name', '')}".strip() for f in founders),
            'founder_locations': ' | '.join(f.get('location', '') for f in founders),
            'founder_linkedin_urls': ' | '.join(f.get('linkedin_url', '') for f in founders)
        })
        agg_rows.append(row)

    agg_fieldnames = list(df.columns) + [
        'total_founders', 'austin_founders', 'has_austin_founder',
        'founder_names', 'founder_locations', 'founder_linkedin_urls'
    ]

    aggregated_csv = "techstars_companies_with_founders_ENRICHED.csv"
    with open(aggregated_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
        writer.writeheader()
        writer.writerows(agg_rows)

    austin_company_count = sum(1 for row in agg_rows if row['has_austin_founder'] == 'TRUE')
    print(f"✅ Aggregated: {aggregated_csv} ({austin_company_count} with Austin founders)")

    austin_companies_csv = "techstars_companies_AUSTIN_FOUNDERS_ONLY_ENRICHED.csv"
    austin_company_rows = [row for row in agg_rows if row['has_austin_founder'] == 'TRUE']
    with open(austin_companies_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
        writer.writeheader()
        writer.writerows(austin_company_rows)

    print(f"✅ Austin companies: {austin_companies_csv} ({len(austin_company_rows):,} rows)\n")

# ============================================================================
# MAIN PIPELINE
# ============================================================================

def main():
    print(f"\n{'='*70}")
    print(f"🚀 COMPLETE FOUNDER ENRICHMENT PIPELINE V2")
    print(f"{'='*70}")
    print(f"FIXED: Improved LinkedIn search (no site: operator)")
    print(f"{'='*70}\n")

    response = input("Continue? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return

    start_time = time.time()

    new_urls = find_missing_linkedin_urls()
    new_locations = enrich_with_brightdata()
    regenerate_csvs()

    elapsed = time.time() - start_time

    print(f"\n{'='*70}")
    print(f"✅ PIPELINE COMPLETE!")
    print(f"{'='*70}")
    print(f"⏱️  Total time: {elapsed/60:.1f} minutes")
    print(f"📊 New LinkedIn URLs: {new_urls:,}")
    print(f"📊 New locations: {new_locations:,}")
    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
