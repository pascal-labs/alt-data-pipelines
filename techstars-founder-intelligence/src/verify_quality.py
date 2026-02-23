#!/usr/bin/env python3
"""
Verify quality of LinkedIn URLs we've found
Check for false positives and mismatches
"""
import json
import re

CHECKPOINT_FILE = "hybrid_final_checkpoint.json"

def load_checkpoint():
    with open(CHECKPOINT_FILE, 'r') as f:
        return json.load(f)

def extract_linkedin_name(url):
    """Extract the name portion from LinkedIn URL"""
    # linkedin.com/in/john-smith-12345 -> john-smith
    match = re.search(r'linkedin\.com/in/([^/?]+)', url)
    if match:
        profile_id = match.group(1)
        # Remove trailing numbers (e.g., john-smith-12345 -> john-smith)
        clean_id = re.sub(r'-\d+$', '', profile_id)
        return clean_id.lower()
    return None

def name_similarity(founder_name, linkedin_id):
    """Check if founder name matches LinkedIn profile ID"""
    if not linkedin_id or not founder_name:
        return False

    founder_lower = founder_name.lower()
    linkedin_lower = linkedin_id.lower()

    # Convert founder name to expected LinkedIn format
    # "John Smith" -> "john-smith" or "johnsmith"
    expected_with_dash = founder_lower.replace(' ', '-')
    expected_no_space = founder_lower.replace(' ', '')

    # 1. Exact match with dash
    if expected_with_dash in linkedin_lower:
        return 'perfect'

    # 2. Exact match without space (e.g., "mandinyambi" for "Mandi Nyambi")
    if expected_no_space in linkedin_lower:
        return 'perfect'

    # 3. Name parts match
    expected_parts = set(founder_lower.split())
    linkedin_parts = set(linkedin_lower.replace('-', ' ').split())

    # At least first AND last name both appear
    if len(expected_parts) >= 2 and len(expected_parts & linkedin_parts) >= 2:
        return 'good'

    # At least one name part matches (for single names or initials)
    overlap = expected_parts & linkedin_parts
    if len(overlap) >= 1:
        return 'partial'

    # Check if all letters from name appear in order in LinkedIn ID
    # E.g., "Caleb Carr" -> "cbcarr" (initials + last name)
    name_letters = ''.join(founder_lower.split())
    linkedin_letters = linkedin_lower.replace('-', '')

    if len(name_letters) <= len(linkedin_letters):
        # Check if it's a reasonable abbreviation
        first_name = founder_lower.split()[0] if founder_lower.split() else ''
        last_name = founder_lower.split()[-1] if len(founder_lower.split()) > 1 else ''

        # Check common patterns: firstlast, flast, firstl, etc.
        patterns = [
            first_name + last_name,  # "calebcarr"
            first_name[0] + last_name if first_name and last_name else '',  # "ccarr"
            first_name + last_name[0] if first_name and last_name else '',  # "calebc"
        ]

        for pattern in patterns:
            if pattern and pattern in linkedin_letters:
                return 'good'

    return False

def analyze_linkedin_urls():
    """Analyze quality of LinkedIn URLs"""
    checkpoint = load_checkpoint()

    total_with_linkedin = 0
    perfect_match = 0
    good_match = 0
    partial_match = 0
    no_match = 0
    suspicious = []

    print(f"\n{'='*70}")
    print(f"🔍 LINKEDIN URL QUALITY ANALYSIS")
    print(f"{'='*70}\n")

    for result in checkpoint['results']:
        company_name = result['company_name']

        for founder in result['founders']:
            linkedin_url = founder.get('linkedin_url', '')
            if not linkedin_url:
                continue

            total_with_linkedin += 1

            first_name = founder.get('first_name', '')
            last_name = founder.get('last_name', '')
            founder_name = f"{first_name} {last_name}".strip()

            linkedin_id = extract_linkedin_name(linkedin_url)

            match_quality = name_similarity(founder_name, linkedin_id)

            if match_quality == 'perfect':
                perfect_match += 1
            elif match_quality == 'good':
                good_match += 1
            elif match_quality == 'partial':
                partial_match += 1
            else:
                no_match += 1
                suspicious.append({
                    'company': company_name,
                    'founder_name': founder_name,
                    'linkedin_url': linkedin_url,
                    'linkedin_id': linkedin_id
                })

    print(f"📊 Total LinkedIn URLs: {total_with_linkedin:,}")
    print(f"✅ Perfect match: {perfect_match:,} ({perfect_match/total_with_linkedin*100:.1f}%)")
    print(f"✅ Good match: {good_match:,} ({good_match/total_with_linkedin*100:.1f}%)")
    print(f"⚠️  Partial match: {partial_match:,} ({partial_match/total_with_linkedin*100:.1f}%)")
    print(f"❌ No match: {no_match:,} ({no_match/total_with_linkedin*100:.1f}%)")

    if suspicious:
        print(f"\n{'='*70}")
        print(f"🚨 SUSPICIOUS URLS (showing first 20)")
        print(f"{'='*70}\n")

        for i, item in enumerate(suspicious[:20], 1):
            print(f"{i}. {item['founder_name']} @ {item['company']}")
            print(f"   URL: {item['linkedin_url']}")
            print(f"   ID:  {item['linkedin_id']}")
            print()

    print(f"\n{'='*70}")
    print(f"💡 QUALITY SCORE: {(perfect_match + good_match + partial_match)/total_with_linkedin*100:.1f}%")
    print(f"   High confidence (perfect + good): {(perfect_match + good_match)/total_with_linkedin*100:.1f}%")
    print(f"{'='*70}\n")

    return {
        'total': total_with_linkedin,
        'perfect': perfect_match,
        'good': good_match,
        'partial': partial_match,
        'no_match': no_match,
        'suspicious': suspicious
    }

if __name__ == "__main__":
    analyze_linkedin_urls()
