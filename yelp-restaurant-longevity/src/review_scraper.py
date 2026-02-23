"""
Phase 2: Scrape oldest review dates from Yelp business pages

This module uses Selenium to visit Yelp pages and extract the oldest review date
for each business. Includes anti-detection measures and CAPTCHA handling.
"""

import logging
from typing import Dict, Optional, Tuple
import pandas as pd
import time
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import random
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class YelpReviewScraper:
    """Scrapes oldest review data from Yelp business pages."""

    def __init__(self, headless: bool = False):
        """
        Initialize the scraper with a Selenium WebDriver.

        Args:
            headless: Whether to run Chrome in headless mode
        """
        self.driver = None
        self.setup_driver(headless)

    def setup_driver(self, headless: bool) -> None:
        """
        Configure Chrome WebDriver with anti-detection measures.

        Args:
            headless: Whether to run in headless mode
        """
        from webdriver_manager.chrome import ChromeDriverManager

        chrome_options = Options()

        # Anti-detection configuration
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument('--disable-blink-features=AutomationControlled')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument(
            'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )

        if headless:
            chrome_options.add_argument('--headless=new')

        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=chrome_options)

        # Hide webdriver property
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )

    def check_captcha(self) -> bool:
        """
        Check if a CAPTCHA is present and handle it.

        Returns:
            True if CAPTCHA was detected, False otherwise
        """
        page_source = self.driver.page_source.lower()
        if 'captcha' in page_source or 'suspicious activity' in page_source:
            logger.warning("⚠️  CAPTCHA detected - Please solve in browser and press Enter")
            input()
            self.driver.refresh()
            time.sleep(3)
            return True
        return False

    def get_oldest_review(self, url: str) -> Optional[Dict[str, str]]:
        """
        Extract the oldest review from a Yelp business page.

        Args:
            url: Yelp business page URL

        Returns:
            Dictionary with review data (date, rating, text, is_closed)
            or None if extraction fails
        """
        try:
            # Add sort parameter to URL
            sorted_url = self._add_sort_parameter(url)

            self.driver.get(sorted_url)
            time.sleep(3)

            # Handle CAPTCHA if present
            self.check_captcha()

            # Check if business is closed
            page_text = self.driver.page_source
            is_closed = "Yelpers report this location has closed" in page_text

            if is_closed:
                logger.warning("⚠️  Business reported CLOSED")

            # Scroll to load review content
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight/2);")
            time.sleep(2)

            soup = BeautifulSoup(self.driver.page_source, 'html.parser')

            # Find the oldest review date
            review_data = self._extract_review_data(soup)
            review_data['is_closed'] = is_closed

            return review_data

        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
            return None

    @staticmethod
    def _add_sort_parameter(url: str) -> str:
        """Add sort_by=date_asc parameter to URL."""
        if '?sort_by=date_asc' in url:
            return url
        return url + '?sort_by=date_asc'

    def _extract_review_data(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract review date, rating, and text from page HTML.

        Args:
            soup: BeautifulSoup object of the page

        Returns:
            Dictionary with date, rating, and text
        """
        all_spans = soup.find_all('span')

        for span in all_spans:
            text = span.text.strip()

            # Filter potential dates
            if not self._is_potential_date(text):
                continue

            # Validate date format
            if self._is_valid_date_format(text):
                # Extract additional review details
                container = self._find_review_container(span)
                review_text = self._extract_review_text(container)
                rating = self._extract_rating(container)

                return {
                    'date': text,
                    'rating': rating,
                    'text': review_text,
                    'is_closed': False  # Will be updated by caller
                }

        return {
            'date': 'No reviews found',
            'rating': 'N/A',
            'text': 'N/A',
            'is_closed': False
        }

    @staticmethod
    def _is_potential_date(text: str) -> bool:
        """Check if text could be a date."""
        if len(text) > 30:
            return False

        # Skip promotional content
        skip_phrases = ['book your', 'save $', 'established', 'founded']
        if any(phrase in text.lower() for phrase in skip_phrases):
            return False

        return True

    @staticmethod
    def _is_valid_date_format(text: str) -> bool:
        """Validate that text matches expected date format."""
        months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

        has_month = any(month in text for month in months)
        has_year = any(str(year) in text for year in range(1990, 2030))

        # Dates should be relatively short
        is_short_enough = len(text) <= 20

        return has_month and has_year and is_short_enough

    @staticmethod
    def _find_review_container(span_element):
        """Find the parent container for the review."""
        container = span_element.parent
        while container and container.name not in ['li', 'div', 'article']:
            container = container.parent
            if not container or container.name == 'body':
                container = span_element.parent.parent
                break
        return container

    @staticmethod
    def _extract_review_text(container) -> str:
        """Extract review text from container."""
        if not container:
            return "N/A"

        for elem in container.find_all('span'):
            text = elem.text.strip()
            if len(text) > 100:
                return text[:500]  # Limit to 500 chars

        return "N/A"

    @staticmethod
    def _extract_rating(container) -> str:
        """Extract star rating from container."""
        if not container:
            return "N/A"

        for elem in container.find_all(['div', 'span']):
            aria_label = elem.get('aria-label', '')
            if 'star rating' in aria_label.lower():
                parts = aria_label.split()
                if parts and parts[0].replace('.', '').isdigit():
                    return parts[0]

        return "N/A"

    def close(self) -> None:
        """Close the WebDriver."""
        if self.driver:
            self.driver.quit()


def process_urls(
    urls_file: str,
    output_file: str,
    headless: bool = False
) -> Tuple[int, int]:
    """
    Process URLs from Phase 1 to extract review data.

    Args:
        urls_file: CSV file with Yelp URLs from Phase 1
        output_file: Output CSV file for results
        headless: Whether to run browser in headless mode

    Returns:
        Tuple of (total_processed, successful_scrapes)
    """
    # Load URLs
    df_urls = pd.read_csv(urls_file)

    # Filter to found URLs
    if 'found' in df_urls.columns:
        df_to_process = df_urls[df_urls['found'] == True].copy()
    else:
        df_to_process = df_urls[
            df_urls['yelp_url'].notna() & (df_urls['yelp_url'] != '')
        ].copy()

    # Ensure sorted URL column exists
    if 'yelp_url_sorted' not in df_to_process.columns:
        df_to_process['yelp_url_sorted'] = df_to_process['yelp_url'].apply(
            lambda x: str(x) + ('?sort_by=date_asc' if '?' not in str(x) else '&sort_by=date_asc')
        )

    logger.info(f"Processing {len(df_to_process)} found businesses...")

    scraper = YelpReviewScraper(headless=headless)
    results = []

    # Resume from existing progress
    processed_ids = set()
    if os.path.exists(output_file):
        existing = pd.read_csv(output_file)
        processed_ids = set(existing['project_location_id'].astype(str))
        results = existing.to_dict('records')

    successful_scrapes = 0

    try:
        for index, row in df_to_process.iterrows():
            # Skip if already processed
            if str(row['project_location_id']) in processed_ids:
                continue

            logger.info(f"\n[{index+1}/{len(df_to_process)}] {row['location_name']}")
            logger.info(f"URL: {row['yelp_url_sorted']}")

            review_data = scraper.get_oldest_review(row['yelp_url_sorted'])

            if review_data:
                if review_data['date'] == 'No reviews found':
                    logger.warning("→ No reviews found")
                else:
                    logger.info(f"→ Found date: {review_data['date']}")
                    successful_scrapes += 1

                result = _build_result_row(row, review_data)
                results.append(result)
                processed_ids.add(str(row['project_location_id']))

                # Save progress every 10 rows
                if len(results) % 10 == 0:
                    pd.DataFrame(results).to_csv(output_file, index=False)
                    logger.info(f"Progress saved: {len(results)} processed")

            # Random delay to avoid rate limiting
            delay = random.uniform(3, 6)
            time.sleep(delay)

    except KeyboardInterrupt:
        logger.info("\nStopped by user")
    finally:
        scraper.close()

        # Save final results
        if results:
            pd.DataFrame(results).to_csv(output_file, index=False)
            logger.info(f"\nResults saved to {output_file}")

    return len(results), successful_scrapes


def _build_result_row(row: pd.Series, review_data: Dict[str, str]) -> Dict:
    """Build result row from review data."""
    return {
        'admin_project_id': row.get('admin_project_id', ''),
        'project_location_id': row.get('project_location_id', ''),
        'location_name': row.get('location_name', ''),
        'project_name': row.get('project_name', ''),
        'address': row.get('address', ''),
        'city': row.get('city', ''),
        'state': row.get('state', ''),
        'yelp_url': row.get('yelp_url', ''),
        'yelp_business_name': row.get('yelp_business_name', row.get('url_business_name', '')),
        'search_strategy': row.get('search_strategy', ''),
        'is_closed': 'Yes' if review_data['is_closed'] else 'No',
        'oldest_review_date': review_data['date'],
        'oldest_review_rating': review_data['rating'],
        'oldest_review_text': review_data['text']
    }


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python review_scraper.py <urls_csv> [output_csv]")
        sys.exit(1)

    urls_csv = sys.argv[1]
    output_csv = sys.argv[2] if len(sys.argv) > 2 else "final_results.csv"

    process_urls(urls_csv, output_csv, headless=False)
