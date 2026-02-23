# alt-data-pipelines

Production-grade alternative data collection pipelines for quantitative research and underwriting analytics.

## Pipelines

### Yelp Restaurant Longevity (`yelp-restaurant-longevity/`)
Systematic extraction of restaurant time-in-business data from Yelp reviews. Analyzed 5,897 restaurants across 50 states for alternative credit risk signals.

- **Two-phase scraping:** Tavily API URL discovery → Selenium review extraction
- **Anti-detection:** Custom user-agents, natural scrolling, random delays
- **Key finding:** 3-year survival mark shows 69% closure risk reduction
- **Scale:** 5,897 restaurants, 92% URL discovery rate, 88% extraction success

### TechStars Founder Intelligence (`techstars-founder-intelligence/`)
AI-powered pipeline for discovering and enriching TechStars founder data. Identified 126 Austin-based founders from 4,042 companies for targeted talent acquisition.

- **Pipeline:** Company scraping → Founder discovery (Tavily) → LinkedIn enrichment (Bright Data) → CSV generation
- **Performance:** 500-850 records/min, $0.017/record (99.7% cost savings vs vendors)
- **Coverage:** 7,642 founders discovered, 87.9% LinkedIn match rate

## Tech Stack
- Python, Selenium, BeautifulSoup, Tavily AI Search, Bright Data
- Pandas for data processing and analysis

## Setup
See individual pipeline directories for setup instructions.
