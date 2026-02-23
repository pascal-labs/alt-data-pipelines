#!/usr/bin/env python3
"""
Process all PENDING_BRIGHTDATA profiles from checkpoint in one massive batch
Run this AFTER the main scraping is complete
"""
import os
import json
from brightdata import bdclient
import time

BRIGHTDATA_API_KEY = os.environ.get("BRIGHTDATA_API_KEY", "your-brightdata-api-key-here")
CHECKPOINT_FILE = "hybrid_final_checkpoint.json"

def load_checkpoint():
    """Load checkpoint file"""
    with open(CHECKPOINT_FILE, 'r') as f:
        return json.load(f)

def save_checkpoint(checkpoint):
    """Save checkpoint file"""
    with open(CHECKPOINT_FILE, 'w') as f:
        json.dump(checkpoint, f, indent=2)

def collect_pending_profiles(checkpoint):
    """Collect all PENDING_BRIGHTDATA profiles from checkpoint"""
    pending = []

    for result in checkpoint.get('results', []):
        for founder in result.get('founders', []):
            if founder.get('location') == 'PENDING_BRIGHTDATA' and founder.get('linkedin_url'):
                pending.append({
                    'founder_name': f"{founder.get('first_name', '')} {founder.get('last_name', '')}".strip(),
                    'linkedin_url': founder.get('linkedin_url'),
                    'company_name': result.get('company_name'),
                    'company_index': result.get('company_index'),
                    'founder_index': result.get('founders', []).index(founder)
                })

    return pending

def process_batch(pending_profiles, batch_size=500):
    """Process pending profiles in batches"""
    brightdata_client = bdclient(api_token=BRIGHTDATA_API_KEY)
    checkpoint = load_checkpoint()

    total = len(pending_profiles)
    print(f"\n{'='*70}")
    print(f"🚀 BRIGHT DATA ENRICHMENT: {total} pending profiles")
    print(f"{'='*70}\n")

    # Process in chunks to avoid massive API calls
    for i in range(0, total, batch_size):
        chunk = pending_profiles[i:i + batch_size]
        chunk_num = (i // batch_size) + 1
        total_chunks = (total + batch_size - 1) // batch_size

        print(f"\n📦 Processing chunk {chunk_num}/{total_chunks} ({len(chunk)} profiles)...")

        # Prepare LinkedIn URLs for Bright Data
        linkedin_urls = [p['linkedin_url'] for p in chunk]

        print(f"   🌐 Sending batch to Bright Data...")

        try:
            # Trigger Bright Data LinkedIn scraping
            response = brightdata_client.scrape_linkedin.profiles(linkedin_urls)

            snapshot_id = response.get('snapshot_id')
            print(f"   ✅ Snapshot created: {snapshot_id}")
            print(f"   ⏳ Polling for results (max 60 attempts = 30 minutes)...")

            # Poll for completion (increased timeout for large batches)
            for attempt in range(60):
                time.sleep(30)

                try:
                    # Download snapshot
                    results = brightdata_client.download_snapshot(snapshot_id)

                    if results and isinstance(results, list) and len(results) > 0:
                        print(f"   ✅ Batch complete! Downloaded {len(results)} profiles...")

                        if results:
                            print(f"   📥 Retrieved {len(results)} LinkedIn profiles")

                        # Update checkpoint with locations
                        updated_count = 0
                        skipped_count = 0
                        for profile in results:
                            linkedin_url = profile.get('url', '')
                            location_field = profile.get('location', '')  # Short city name
                            city = profile.get('city', '')  # Full location string
                            country_code = profile.get('country_code', '')

                            # Accept ANY location data - prefer full location string (city), then short city (location), then country
                            if city:
                                location = city  # Full location like "Austin, Texas, United States"
                            elif location_field:
                                location = location_field  # Short city like "Austin"
                            elif country_code:
                                location = country_code
                            else:
                                # No location data at all - skip
                                skipped_count += 1
                                continue

                            # Find matching founder in checkpoint
                            for pending in chunk:
                                if pending['linkedin_url'] == linkedin_url:
                                    # Update in checkpoint
                                    company_index = pending['company_index']
                                    founder_index = pending['founder_index']

                                    for result in checkpoint['results']:
                                        if result['company_index'] == company_index:
                                            if founder_index < len(result['founders']):
                                                result['founders'][founder_index]['location'] = location

                                                # Check if Austin
                                                is_austin = any(keyword in location.lower() for keyword in ['austin', 'atx'])
                                                result['founders'][founder_index]['is_austin'] = is_austin

                                                updated_count += 1
                                                print(f"      ✅ {pending['founder_name']}: {location}")
                                            break

                        print(f"   ✅ Updated {updated_count} founder locations")

                        # Save checkpoint after each chunk
                        save_checkpoint(checkpoint)
                        print(f"   💾 Checkpoint saved")
                        break
                    else:
                        print(f"   ⏳ Attempt {attempt + 1}/60: Still processing...")

                except Exception as poll_error:
                    print(f"   ⚠️  Poll error: {str(poll_error)}")
                    continue

            else:
                print(f"   ⚠️  Timeout after 30 minutes - some profiles may not be enriched")

        except Exception as e:
            print(f"   ❌ Batch error: {str(e)}")
            continue

    print(f"\n{'='*70}")
    print(f"✅ All batches processed!")
    print(f"💾 Final checkpoint saved to: {CHECKPOINT_FILE}")
    print(f"{'='*70}\n")

def main():
    """Main function"""
    print("\n" + "="*70)
    print("🔄 BRIGHT DATA PENDING PROFILE ENRICHMENT")
    print("="*70)

    # Load checkpoint
    checkpoint = load_checkpoint()

    # Collect all pending profiles
    pending = collect_pending_profiles(checkpoint)

    if not pending:
        print("\n✅ No pending profiles found - all done!")
        return

    print(f"\n📊 Found {len(pending)} PENDING_BRIGHTDATA profiles")

    # Confirm
    response = input(f"\n❓ Process all {len(pending)} profiles with Bright Data? (y/n): ")
    if response.lower() != 'y':
        print("❌ Cancelled")
        return

    # Process
    process_batch(pending, batch_size=5714)

if __name__ == "__main__":
    main()
