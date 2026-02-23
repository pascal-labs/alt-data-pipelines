"""
Phase 1: Find Yelp URLs using Tavily API

This module implements a multi-strategy search approach to find Yelp business pages
using the Tavily search API. It's designed to be fast and avoid CAPTCHAs.
"""

import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
import requests
import time
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YelpURLFinder:
    """Finds Yelp URLs for businesses using the Tavily search API."""

    def __init__(self, api_key: str):
        """
        Initialize the URL finder.

        Args:
            api_key: Tavily API key for search requests
        """
        self.api_key = api_key
        self.base_url = "https://api.tavily.com"

    def search_business(
        self,
        location_name: str,
        city: str,
        state: str,
        address: Optional[str] = None,
        project_name: Optional[str] = None
    ) -> Optional[Dict[str, str]]:
        """
        Try multiple search strategies to find the best Yelp match.

        This method implements a cascading search strategy, trying more specific
        searches first and falling back to broader searches if needed.

        Args:
            location_name: Name of the business location
            city: City where business is located
            state: State where business is located
            address: Optional street address for more specific search
            project_name: Optional alternate name for the business

        Returns:
            Dictionary with URL and metadata if found, None otherwise
        """
        searches = self._build_search_strategies(
            location_name, city, state, address, project_name
        )

        for search in searches:
            logger.info(f"Trying: {search['strategy']} - {search['query']}")

            result = self._search_yelp(search['query'])
            if result:
                result['search_strategy'] = search['strategy']
                result['search_query'] = search['query']
                return result

        return None

    def _build_search_strategies(
        self,
        location_name: str,
        city: str,
        state: str,
        address: Optional[str],
        project_name: Optional[str]
    ) -> List[Dict[str, str]]:
        """
        Build a prioritized list of search strategies.

        Returns:
            List of search dictionaries with 'query' and 'strategy' keys
        """
        searches = []

        # Strategy 1: Name with street name (most specific)
        if address and not pd.isna(address) and str(address).strip():
            street_only = self._extract_street_name(str(address))
            if street_only:
                searches.append({
                    'query': f"{location_name} {street_only} {city} {state}",
                    'strategy': 'name_street_city_state'
                })

        # Strategy 2: Name with city/state only
        searches.append({
            'query': f"{location_name} {city} {state}",
            'strategy': 'name_city_state'
        })

        # Strategy 3: Project name if different
        if project_name and project_name != location_name:
            searches.append({
                'query': f"{project_name} {city} {state}",
                'strategy': 'project_name'
            })

        # Strategy 4: Base name (before dash/em-dash)
        base_name = location_name.split('–')[0].split('—')[0].split('-')[0].strip()
        if base_name != location_name:
            searches.append({
                'query': f"{base_name} {city} {state}",
                'strategy': 'base_name'
            })

        return searches

    @staticmethod
    def _extract_street_name(address: str) -> str:
        """
        Extract street name from full address by removing house numbers.

        Example: "501 Brazos Street" -> "Brazos Street"
        """
        return ' '.join([
            word for word in address.split()
            if not word[0].isdigit()
        ])

    def _search_yelp(self, query: str) -> Optional[Dict[str, str]]:
        """
        Execute a search query via Tavily API.

        Args:
            query: Search query string

        Returns:
            Dictionary with URL and metadata if found, None otherwise
        """
        search_query = f"{query} site:yelp.com"

        try:
            response = requests.post(
                f"{self.base_url}/search",
                json={
                    "api_key": self.api_key,
                    "query": search_query,
                    "search_depth": "basic",
                    "include_domains": ["yelp.com"],
                    "max_results": 5
                },
                timeout=10
            )

            if response.status_code == 200:
                results = response.json()

                # Look for Yelp business pages
                for result in results.get('results', []):
                    url = result.get('url', '')
                    if '/biz/' in url and 'yelp.com' in url:
                        clean_url = url.split('?')[0]
                        biz_name = clean_url.split('/biz/')[-1].replace('-', ' ').title()

                        return {
                            'url': clean_url,
                            'title': result.get('title', ''),
                            'snippet': result.get('snippet', ''),
                            'url_business_name': biz_name
                        }
        except Exception as e:
            logger.error(f"Search error: {e}")

        return None


def process_csv(
    input_file: str,
    output_file: str,
    api_key: str
) -> Tuple[int, int]:
    """
    Process input CSV to find all Yelp URLs.

    Args:
        input_file: Path to input CSV with business data
        output_file: Path to save results CSV
        api_key: Tavily API key

    Returns:
        Tuple of (total_processed, found_count)
    """
    finder = YelpURLFinder(api_key)
    results = []

    # Resume from existing progress if available
    start_row = 0
    if os.path.exists(output_file):
        existing = pd.read_csv(output_file)
        results = existing.to_dict('records')
        start_row = len(results)
        logger.info(f"Resuming from row {start_row}")

    df = pd.read_csv(input_file)
    total = len(df)

    logger.info(f"Processing {total - start_row} businesses...")

    for index, row in df.iloc[start_row:].iterrows():
        location_name = row['Location Name']
        city = row['City']
        state = row['State']
        address = row.get('Address', '')
        project_name = row.get('Project Name (from Locations)', '')

        # Handle NaN values
        if pd.isna(address):
            address = ''

        logger.info(f"\n[{index+1}/{total}] {location_name} - {city}, {state}")

        result = finder.search_business(
            location_name, city, state, address, project_name
        )

        row_result = _build_result_row(row, result, location_name, city, state, address, project_name)
        results.append(row_result)

        if result:
            logger.info(f"✓ Found: {result['url']}")
        else:
            logger.warning(f"✗ Not found")

        # Save progress periodically
        if (index + 1) % 50 == 0:
            pd.DataFrame(results).to_csv(output_file, index=False)
            logger.info(f"Saved progress: {len(results)} URLs processed")

        time.sleep(0.5)  # Rate limiting

    # Final save
    pd.DataFrame(results).to_csv(output_file, index=False)

    found_count = sum(1 for r in results if r['found'])
    logger.info(f"\n{'='*60}")
    logger.info(f"Phase 1 Complete!")
    logger.info(f"Found {found_count}/{len(results)} businesses on Yelp")
    logger.info(f"Results saved to: {output_file}")
    logger.info(f"{'='*60}")

    return len(results), found_count


def _build_result_row(
    row: pd.Series,
    result: Optional[Dict[str, str]],
    location_name: str,
    city: str,
    state: str,
    address: str,
    project_name: str
) -> Dict[str, any]:
    """Build a result row dictionary from search results."""
    base_data = {
        'admin_project_id': row.get('Admin Project ID', ''),
        'project_location_id': row.get('Project Location ID', ''),
        'location_name': location_name,
        'project_name': project_name,
        'address': address,
        'city': city,
        'state': state,
    }

    if result:
        return {
            **base_data,
            'yelp_url': result['url'],
            'yelp_url_sorted': result['url'] + '?sort_by=date_asc',
            'yelp_title': result['title'],
            'url_business_name': result['url_business_name'],
            'search_strategy': result['search_strategy'],
            'search_query': result['search_query'],
            'found': True
        }
    else:
        return {
            **base_data,
            'yelp_url': '',
            'yelp_url_sorted': '',
            'yelp_title': '',
            'url_business_name': '',
            'search_strategy': '',
            'search_query': '',
            'found': False
        }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: python url_finder.py <input_csv> <output_csv> <api_key>")
        sys.exit(1)

    input_csv = sys.argv[1]
    output_csv = sys.argv[2]
    tavily_key = sys.argv[3]

    process_csv(input_csv, output_csv, tavily_key)
