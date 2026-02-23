#!/usr/bin/env python3
"""
Fix the layering - use proper pandas index matching
"""
import json
import csv
import pandas as pd

COMPANIES_CSV = "data/input/techstars_companies_clean.csv"
CHECKPOINT_FILE = "data/checkpoints/hybrid_final_checkpoint.json"

print("Loading checkpoint...")
with open(CHECKPOINT_FILE, 'r') as f:
    checkpoint = json.load(f)

# Create mapping from company_index to founders data
index_to_founders = {}
for result in checkpoint['results']:
    company_index = result['company_index']
    founders = result.get('founders', [])
    index_to_founders[company_index] = founders

print(f"✅ Loaded {len(index_to_founders)} companies with founder data")
print(f"   Index range: {min(index_to_founders.keys())} to {max(index_to_founders.keys())}\n")

# Load companies CSV with pandas to get proper indexes
df = pd.read_csv(COMPANIES_CSV)
print(f"✅ Loaded {len(df)} companies from CSV")
print(f"   DataFrame index range: {df.index.min()} to {df.index.max()}\n")

# Verify alignment with a few examples
print("🔍 Verifying alignment:")
for idx in list(index_to_founders.keys())[:5]:
    if idx < len(df):
        company_name = df.iloc[idx]['name']
        checkpoint_name = None
        for result in checkpoint['results']:
            if result['company_index'] == idx:
                checkpoint_name = result['company_name']
                break
        print(f"   Index {idx}: CSV='{company_name}' vs Checkpoint='{checkpoint_name}' - {'✅ MATCH' if company_name == checkpoint_name else '❌ MISMATCH'}")

print("\n" + "="*70)
print("Creating corrected expanded CSV...")
print("="*70 + "\n")

# Create expanded version with correct indexing
output_csv = "data/output/techstars_companies_expanded_by_founder_ENRICHED.csv"

rows = []
austin_count = 0

for idx, company_row in df.iterrows():
    founders = index_to_founders.get(idx, [])

    if not founders:
        # No founders found - write company with empty founder fields
        row = company_row.to_dict()
        row['founder_first_name'] = ''
        row['founder_last_name'] = ''
        row['founder_full_name'] = ''
        row['founder_linkedin_url'] = ''
        row['founder_location'] = ''
        row['founder_is_austin'] = 'FALSE'
        rows.append(row)
    else:
        # Write one row per founder
        for founder in founders:
            row = company_row.to_dict()
            row['founder_first_name'] = founder.get('first_name', '')
            row['founder_last_name'] = founder.get('last_name', '')
            row['founder_full_name'] = f"{founder.get('first_name', '')} {founder.get('last_name', '')}".strip()
            row['founder_linkedin_url'] = founder.get('linkedin_url', '')
            row['founder_location'] = founder.get('location', '')
            row['founder_is_austin'] = 'TRUE' if founder.get('is_austin', False) else 'FALSE'
            rows.append(row)

            if founder.get('is_austin', False):
                austin_count += 1

# Write to CSV
fieldnames = list(df.columns) + [
    'founder_first_name',
    'founder_last_name',
    'founder_full_name',
    'founder_linkedin_url',
    'founder_location',
    'founder_is_austin'
]

with open(output_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

print(f"✅ Created {len(rows)} rows")
print(f"🎯 {austin_count} Austin founders")
print(f"💾 Saved to: {output_csv}\n")

# Create Austin-only version
austin_only_csv = "data/output/techstars_companies_expanded_AUSTIN_FOUNDERS_ONLY_ENRICHED.csv"
austin_rows = [row for row in rows if row['founder_is_austin'] == 'TRUE']

with open(austin_only_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(austin_rows)

print(f"✅ Austin-only: {austin_only_csv} ({len(austin_rows)} rows)\n")

# Also create aggregated version
print("Creating aggregated company view...")
aggregated_csv = "data/output/techstars_companies_with_founders_ENRICHED.csv"

agg_rows = []
for idx, company_row in df.iterrows():
    founders = index_to_founders.get(idx, [])

    row = company_row.to_dict()
    row['total_founders'] = len(founders)
    row['austin_founders'] = sum(1 for f in founders if f.get('is_austin', False))
    row['has_austin_founder'] = 'TRUE' if row['austin_founders'] > 0 else 'FALSE'
    row['founder_names'] = ' | '.join(f"{f.get('first_name', '')} {f.get('last_name', '')}".strip() for f in founders)
    row['founder_locations'] = ' | '.join(f.get('location', '') for f in founders)
    row['founder_linkedin_urls'] = ' | '.join(f.get('linkedin_url', '') for f in founders)

    agg_rows.append(row)

agg_fieldnames = list(df.columns) + [
    'total_founders',
    'austin_founders',
    'has_austin_founder',
    'founder_names',
    'founder_locations',
    'founder_linkedin_urls'
]

with open(aggregated_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
    writer.writeheader()
    writer.writerows(agg_rows)

austin_company_count = sum(1 for row in agg_rows if row['has_austin_founder'] == 'TRUE')
print(f"✅ Aggregated: {aggregated_csv}")
print(f"   {austin_company_count} companies with Austin founders\n")

# Austin companies only
austin_companies_csv = "data/output/techstars_companies_AUSTIN_FOUNDERS_ONLY_ENRICHED.csv"
austin_company_rows = [row for row in agg_rows if row['has_austin_founder'] == 'TRUE']

with open(austin_companies_csv, 'w', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=agg_fieldnames)
    writer.writeheader()
    writer.writerows(austin_company_rows)

print(f"✅ Austin companies only: {austin_companies_csv} ({len(austin_company_rows)} rows)\n")
