"""
SMART Founder Search with Checkpoint/Resume
- Saves progress after every company
- Can resume from where it left off
- Won't re-search companies already processed
- Incremental saves to avoid data loss
"""
import pandas as pd
import json
import os
from datetime import datetime

class FounderSearchCheckpoint:
    """Manages checkpoints for resumable searches"""

    def __init__(self, checkpoint_file='founder_search_checkpoint.json'):
        self.checkpoint_file = checkpoint_file
        self.checkpoint = self.load_checkpoint()

    def load_checkpoint(self):
        """Load existing checkpoint or create new one"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                return json.load(f)
        else:
            return {
                'last_processed_index': -1,
                'total_processed': 0,
                'results': [],
                'started_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat(),
                'status': 'initialized'
            }

    def save_checkpoint(self):
        """Save current progress"""
        self.checkpoint['last_updated'] = datetime.now().isoformat()
        with open(self.checkpoint_file, 'w') as f:
            json.dump(self.checkpoint, f, indent=2)

    def add_result(self, company_result):
        """Add a company result and save checkpoint"""
        self.checkpoint['results'].append(company_result)
        self.checkpoint['total_processed'] += 1
        self.checkpoint['last_processed_index'] = company_result['company_index']
        self.save_checkpoint()

    def get_next_batch(self, batch_size=10, max_total=None):
        """Get next batch of companies to process"""
        df = pd.read_csv('techstars_companies_clean.csv')

        # Start from last processed + 1
        start_idx = self.checkpoint['last_processed_index'] + 1

        # If max_total specified, don't exceed it
        if max_total and self.checkpoint['total_processed'] >= max_total:
            return []

        # Calculate how many more to process
        if max_total:
            remaining = max_total - self.checkpoint['total_processed']
            batch_size = min(batch_size, remaining)

        # Get batch
        end_idx = min(start_idx + batch_size, len(df))
        batch_df = df.iloc[start_idx:end_idx]

        companies = []
        for idx, row in batch_df.iterrows():
            companies.append({
                'company_index': idx,
                'company_name': row['name'],
                'company_year': row.get('year', ''),
                'company_location': row.get('location', ''),
                'website': row.get('website', ''),
                'crunchbase': row.get('crunchbase', ''),
                'linkedin': row.get('linkedin', '')
            })

        return companies

    def export_results(self, filename=None):
        """Export all results to CSV"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'founder_search_results_{timestamp}.csv'

        # Flatten results for CSV
        flattened = []
        for company in self.checkpoint['results']:
            base_data = {
                'company_index': company['company_index'],
                'company_name': company['company_name'],
                'company_year': company.get('company_year', ''),
                'company_location': company.get('company_location', ''),
                'founder_count': len(company.get('founders', [])),
                'austin_founders_count': company.get('austin_founders_count', 0)
            }

            if company.get('founders'):
                # One row per founder
                for founder in company['founders']:
                    # Parse first and last name from full name
                    full_name = founder.get('name', '')
                    name_parts = full_name.split()

                    first_name = name_parts[0] if len(name_parts) > 0 else ''
                    last_name = ' '.join(name_parts[1:]) if len(name_parts) > 1 else ''

                    row = {
                        **base_data,
                        'founder_first_name': first_name,
                        'founder_last_name': last_name,
                        'founder_full_name': full_name,
                        **{k: v for k, v in founder.items() if k != 'name'}
                    }
                    flattened.append(row)
            else:
                # Company with no founders found
                flattened.append(base_data)

        df = pd.DataFrame(flattened)
        df.to_csv(filename, index=False)

        # Also save Austin founders only
        if 'is_austin' in df.columns:
            austin_df = df[df['is_austin'] == True].copy()
            austin_file = filename.replace('.csv', '_AUSTIN_ONLY.csv')
            austin_df.to_csv(austin_file, index=False)
            print(f"📍 Austin founders: {austin_file} ({len(austin_df)} founders)")

        print(f"💾 All results: {filename} ({len(df)} rows)")
        return filename

    def get_status(self):
        """Print current status"""
        print("=" * 70)
        print("📊 FOUNDER SEARCH STATUS")
        print("=" * 70)
        print(f"Started: {self.checkpoint.get('started_at', 'N/A')}")
        print(f"Last updated: {self.checkpoint.get('last_updated', 'N/A')}")
        print(f"Companies processed: {self.checkpoint['total_processed']}")
        print(f"Last index: {self.checkpoint['last_processed_index']}")

        # Count Austin founders
        austin_count = 0
        for company in self.checkpoint['results']:
            austin_count += company.get('austin_founders_count', 0)

        print(f"Austin founders found: {austin_count}")
        print("=" * 70)

        return {
            'total_processed': self.checkpoint['total_processed'],
            'austin_founders': austin_count,
            'can_resume': True
        }

    def reset(self):
        """Reset checkpoint (start over)"""
        if os.path.exists(self.checkpoint_file):
            # Backup old checkpoint
            backup = self.checkpoint_file.replace('.json', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json')
            os.rename(self.checkpoint_file, backup)
            print(f"📦 Backed up old checkpoint to: {backup}")

        self.checkpoint = {
            'last_processed_index': -1,
            'total_processed': 0,
            'results': [],
            'started_at': datetime.now().isoformat(),
            'last_updated': datetime.now().isoformat(),
            'status': 'reset'
        }
        self.save_checkpoint()
        print("🔄 Checkpoint reset. Starting fresh.")

def main():
    """Demo the checkpoint system"""
    checkpoint = FounderSearchCheckpoint()

    # Show current status
    status = checkpoint.get_status()

    print("\n📋 COMMANDS:")
    print("  checkpoint.get_status()        - Show current progress")
    print("  checkpoint.get_next_batch(10)  - Get next 10 companies to process")
    print("  checkpoint.add_result(data)    - Save a company result")
    print("  checkpoint.export_results()    - Export to CSV")
    print("  checkpoint.reset()             - Start over (backs up current)")
    print()

    # Check if we can resume
    if status['total_processed'] > 0:
        print(f"✅ Can resume from company index {checkpoint.checkpoint['last_processed_index'] + 1}")
        print(f"   Already processed: {status['total_processed']} companies")
        print(f"   Found: {status['austin_founders']} Austin founders so far")
    else:
        print("🆕 Starting fresh search")

    print("\n💡 Usage:")
    print("   from smart_founder_search import FounderSearchCheckpoint")
    print("   cp = FounderSearchCheckpoint()")
    print("   batch = cp.get_next_batch(10)  # Get next 10 companies")
    print("   # ... process batch with Tavily ...")
    print("   cp.add_result(company_data)    # Saves automatically")

if __name__ == "__main__":
    main()
