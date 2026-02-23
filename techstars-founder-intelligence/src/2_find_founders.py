#!/usr/bin/env python3
"""
Get ALL Founder Locations (not just Austin)
Captures current location for every founder found

Usage:
    python3 run_founder_search_all_locations.py --batch 100
    python3 run_founder_search_all_locations.py --batch 4042
"""
import os
import argparse
import time
import random
import re
from tavily import TavilyClient
from smart_founder_search import FounderSearchCheckpoint

# Initialize Tavily client
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "your-tavily-api-key-here")
tavily = TavilyClient(api_key=TAVILY_API_KEY)

def parse_founders_from_results(results, company_name):
    """Extract founder names - IMPROVED with better patterns"""
    founders = []
    found_names = set()

    if not results or 'results' not in results:
        return founders

    for result in results.get('results', []):
        url = result.get('url', '')
        title = result.get('title', '')
        content = result.get('content', '')
        combined = f"{title} {content}"

        # HIGH PRIORITY: Crunchbase has best data
        if 'crunchbase.com' in url:
            # "Founders Name1, Name2, Name3"
            cb_match = re.search(r'Founders?\s+([A-Z][a-z]+\s+[A-Z][a-z]+(?:\s*,\s*[A-Z][a-z]+\s+[A-Z][a-z]+)*)', combined)
            if cb_match:
                names_str = cb_match.group(1)
                for name in names_str.split(','):
                    name = name.strip()
                    if name and len(name) > 3 and name not in found_names:
                        founders.append({'name': name, 'source_url': url, 'confidence': 'HIGH'})
                        found_names.add(name)
                continue

        # "Name and Name LastName" (e.g., "Ben and Moisey Uretsky")
        and_pattern = r'([A-Z][a-z]+)\s+and\s+([A-Z][a-z]+)\s+([A-Z][a-z]+)'
        for match in re.finditer(and_pattern, combined):
            context = combined[max(0, match.start()-50):match.end()+50]
            if any(word in context.lower() for word in ['founder', 'co-founder', 'ceo', 'started']):
                name1 = f"{match.group(1)} {match.group(3)}"
                name2 = f"{match.group(2)} {match.group(3)}"
                if name1 not in found_names:
                    founders.append({'name': name1, 'source_url': url, 'confidence': 'HIGH'})
                    found_names.add(name1)
                if name2 not in found_names:
                    founders.append({'name': name2, 'source_url': url, 'confidence': 'HIGH'})
                    found_names.add(name2)

        # "founder FullName" or "co-founder FullName"
        for match in re.finditer(r'(?:co-)?founder[,\s:]+([A-Z][a-z]+\s+[A-Z][a-z]+)', combined, re.IGNORECASE):
            name = match.group(1).strip()
            bad_words = ['and', 'the', 'former', 'current', 'ceo', 'chief', 'officer']
            if name and len(name) > 3 and name not in found_names and not any(w in name.lower() for w in bad_words):
                confidence = "HIGH" if 'crunchbase.com' in url else "MEDIUM"
                founders.append({'name': name, 'source_url': url, 'confidence': confidence})
                found_names.add(name)

    return founders

def get_founder_location(founder_name, company_name):
    """Get founder's CURRENT location from LinkedIn"""
    query = f'"{founder_name}" LinkedIn profile'

    try:
        results = tavily.search(query=query, max_results=5, search_depth="basic")

        # Common location patterns
        location_patterns = [
            r'Location[:\s]*([A-Z][^\.]{3,60}(?:United States|USA|UK|Canada|India|Israel|Singapore|Australia|Germany|France|Spain|Brazil|Mexico|Argentina|Colombia|Chile|Peru|Netherlands|Switzerland|Sweden|Denmark|Norway|Finland|Ireland|Belgium|Austria|Portugal|Poland|Czech Republic|Romania|Hungary|Greece|Turkey|UAE|Saudi Arabia|Egypt|South Africa|Kenya|Nigeria|Ghana|Japan|South Korea|China|Hong Kong|Taiwan|Thailand|Vietnam|Malaysia|Philippines|Indonesia|New Zealand))',
            r'Based in[:\s]*([A-Z][^\.]{3,60})',
            r'Lives in[:\s]*([A-Z][^\.]{3,60})',
            r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*,\s*(?:[A-Z]{2}|[A-Z][a-z]+)(?:,\s*United States)?)'
        ]

        for result in results.get('results', []):
            url = result.get('url', '')
            title = result.get('title', '')
            content = result.get('content', '')

            # Must be a LinkedIn profile
            if 'linkedin.com/in/' not in url:
                continue

            combined = title + " " + content

            # Try to extract location
            for pattern in location_patterns:
                match = re.search(pattern, combined)
                if match:
                    location = match.group(1).strip()

                    # Clean up location
                    location = re.sub(r'\s+', ' ', location)  # Normalize spaces
                    location = location.split('.')[0]  # Remove trailing sentences

                    # Check if it's Austin area
                    is_austin = bool(re.search(r'\b(?:Austin|Round Rock|Georgetown|Cedar Park|Pflugerville|Leander|Kyle|Buda|Lakeway|Bee Cave|Dripping Springs|Hutto|Manor)\b', location, re.IGNORECASE))

                    return {
                        'linkedin_url': url,
                        'current_location': location,
                        'is_austin': is_austin,
                        'confidence': 'HIGH',
                        'verification_method': 'LinkedIn location field'
                    }

            # LinkedIn found but no clear location
            return {
                'linkedin_url': url,
                'current_location': 'UNKNOWN',
                'is_austin': False,
                'confidence': 'MEDIUM',
                'verification_method': 'LinkedIn no location'
            }

        # No LinkedIn profile found
        return {
            'linkedin_url': '',
            'current_location': 'UNKNOWN',
            'is_austin': False,
            'confidence': 'LOW',
            'verification_method': 'No LinkedIn found'
        }

    except Exception as e:
        print(f"    ⚠️  Error checking location: {e}")
        return {
            'linkedin_url': '',
            'current_location': 'ERROR',
            'is_austin': False,
            'confidence': 'ERROR',
            'verification_method': 'Error'
        }

def process_company(company_data, index, total):
    """Process one company - find founders and get ALL their locations"""
    company_name = company_data['company_name']

    print(f"\n{'='*70}")
    print(f"[{index}/{total}] 🏢 {company_name}")
    print(f"{'='*70}")

    # STEP 1: Find founders
    print(f"  🔍 STEP 1: Searching for founders...")
    query = f"{company_name} founders"

    try:
        results = tavily.search(query=query, max_results=5, search_depth="basic")
        founders = parse_founders_from_results(results, company_name)

        if founders:
            print(f"  ✅ Found {len(founders)} founder(s):")
            for f in founders:
                print(f"     - {f['name']} (confidence: {f['confidence']})")
        else:
            print(f"  ⚠️  No founders found")

        # Random delay between 1-3 seconds for human-like pattern
        time.sleep(random.uniform(1.0, 3.0))

        # STEP 2: Get location for each founder
        austin_count = 0
        founder_details = []

        for founder in founders:
            print(f"\n  🔍 STEP 2: Getting location for {founder['name']}...")

            location_info = get_founder_location(founder['name'], company_name)

            founder_detail = {
                'name': founder['name'],
                'linkedin_url': location_info['linkedin_url'],
                'current_location': location_info['current_location'],
                'is_austin': location_info['is_austin'],
                'confidence': location_info['confidence'],
                'source_url': founder['source_url'],
                'verification_method': location_info.get('verification_method', 'N/A')
            }

            if location_info['is_austin']:
                print(f"  🎯 AUSTIN! {founder['name']}")
                print(f"     Location: {location_info['current_location']}")
                print(f"     LinkedIn: {location_info['linkedin_url']}")
                austin_count += 1
            else:
                loc = location_info['current_location']
                print(f"     📍 {founder['name']}: {loc}")

            founder_details.append(founder_detail)
            # Random delay between 0.5-2 seconds for human-like pattern
            time.sleep(random.uniform(0.5, 2.0))

        # Compile result
        result = {
            'company_index': company_data['company_index'],
            'company_name': company_name,
            'company_year': company_data.get('company_year', ''),
            'company_location': company_data.get('company_location', ''),
            'founders': founder_details,
            'austin_founders_count': austin_count
        }

        if austin_count > 0:
            print(f"\n  🎉 {company_name}: {austin_count} Austin founder(s)! ✅")
        else:
            print(f"\n  ✓ {company_name}: Complete (founders in other cities)")

        return result

    except Exception as e:
        print(f"  ❌ Error: {e}")
        return {
            'company_index': company_data['company_index'],
            'company_name': company_name,
            'company_year': company_data.get('company_year', ''),
            'company_location': company_data.get('company_location', ''),
            'founders': [],
            'austin_founders_count': 0,
            'error': str(e)
        }

def main():
    parser = argparse.ArgumentParser(description='Find ALL TechStars founder locations')
    parser.add_argument('--batch', type=int, default=10, help='Number of companies to process')
    parser.add_argument('--resume', action='store_true', help='Resume from checkpoint')
    parser.add_argument('--status', action='store_true', help='Show status and exit')

    args = parser.parse_args()

    print("\n" + "="*70)
    print("🌍 TECHSTARS FOUNDER LOCATION SEARCH (ALL CITIES)")
    print("="*70 + "\n")

    # Initialize checkpoint
    cp = FounderSearchCheckpoint()

    if args.status:
        cp.get_status()
        return

    # Get next batch
    batch = cp.get_next_batch(batch_size=args.batch)

    if not batch:
        print("✅ All companies processed!")
        cp.export_results()
        return

    print(f"📋 Processing {len(batch)} companies...")
    print(f"⏱️  Estimated time: ~{len(batch) * 15} seconds")
    print(f"🎯 Goal: Get CURRENT LOCATION for all founders")
    print()

    start_time = time.time()

    # Process each company
    for i, company in enumerate(batch, 1):
        result = process_company(company,
                                cp.checkpoint['total_processed'] + i,
                                cp.checkpoint['total_processed'] + len(batch))

        # Save checkpoint after each company
        cp.add_result(result)
        print(f"  💾 Progress saved (checkpoint updated)")

    elapsed = time.time() - start_time

    # Final summary
    print("\n" + "="*70)
    print("📊 BATCH COMPLETE")
    print("="*70)
    print(f"Time: {elapsed:.1f} seconds ({elapsed/len(batch):.1f}s per company)")
    print()

    cp.get_status()
    print()
    cp.export_results()

if __name__ == "__main__":
    main()
