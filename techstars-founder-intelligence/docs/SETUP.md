# Setup Guide

Complete installation and configuration guide for the TechStars Austin Recruiting Pipeline.

## Prerequisites

### System Requirements
- **Python**: 3.9 or higher
- **OS**: macOS, Linux, or Windows
- **Memory**: 4GB RAM minimum (8GB recommended)
- **Storage**: 500MB free space

### API Keys Required

1. **Tavily AI Search API** (Production)
   - Sign up: https://tavily.com/
   - Pricing: Pay-as-you-go or subscription
   - Usage: ~1000-2000 searches per full run

2. **Bright Data Scraping Browser API**
   - Sign up: https://brightdata.com/
   - Pricing: Pay per successful scrape
   - Usage: ~6000 LinkedIn profiles per full run

## Installation

### 1. Clone Repository

```bash
git clone https://github.com/[username]/techstars-austin-recruiting.git
cd techstars-austin-recruiting
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

**Dependencies:**
- `pandas` - Data manipulation
- `tavily-python` - Tavily API client
- `brightdata` - Bright Data SDK
- `requests` - HTTP requests

### 3. Configure API Keys

Copy the configuration template:
```bash
cp config.py.example config.py
```

Edit `config.py` with your actual API keys:
```python
# config.py
TAVILY_API_KEY = "tvly-prod-YOUR-KEY-HERE"
BRIGHTDATA_API_KEY = "YOUR-BRIGHTDATA-KEY-HERE"
```

**⚠️ IMPORTANT**: Never commit `config.py` to git (it's in `.gitignore`)

## Running the Pipeline

### Option 1: Full Pipeline (Recommended for First Run)

Runs all steps in sequence:
```bash
python src/pipeline.py
```

**What it does:**
1. Finds founders without LinkedIn URLs (if any)
2. Enriches with Bright Data
3. Generates final CSVs

**Time estimate**: 15-30 minutes depending on API rates

### Option 2: Individual Steps

Run specific pipeline stages:

#### Step 1: Find Founders (Optional - if you need more LinkedIn URLs)
```bash
python src/2_find_founders.py --batch 1074
```

#### Step 2: Enrich Locations
```bash
python src/3_enrich_locations.py
```

#### Step 3: Generate CSVs
```bash
python src/4_generate_csvs.py
```

## Output Files

### Generated CSVs (in `data/output/`)

1. **techstars_companies_expanded_by_founder_ENRICHED.csv**
   - Format: One row per founder
   - Rows: ~7,600
   - Use: Individual founder analysis

2. **techstars_companies_expanded_AUSTIN_FOUNDERS_ONLY_ENRICHED.csv**
   - Format: One row per Austin founder
   - Rows: ~124
   - Use: Recruiting outreach list

3. **techstars_companies_with_founders_ENRICHED.csv**
   - Format: One row per company (founders pipe-separated)
   - Rows: 4,042
   - Use: Company-level analysis

4. **techstars_companies_AUSTIN_FOUNDERS_ONLY_ENRICHED.csv**
   - Format: Companies with Austin founders
   - Rows: ~96
   - Use: Company targeting

## Troubleshooting

### API Rate Limits

**Problem**: `UsageLimitExceededError` or `ForbiddenError`

**Solution**:
1. Check API dashboard for usage limits
2. Add credits to your account
3. Wait for rate limit reset (varies by plan)
4. Use `--batch` parameter to process smaller chunks

### File Not Found Errors

**Problem**: `FileNotFoundError: hybrid_final_checkpoint.json`

**Solution**:
Ensure you're running from the project root:
```bash
cd techstars-austin-recruiting
python src/pipeline.py  # Not src/
```

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'config'`

**Solution**:
1. Ensure `config.py` exists (copy from `config.py.example`)
2. Run from project root (not from `src/` directory)

### Low Success Rates

**Problem**: Very few LinkedIn URLs found

**Possible causes**:
1. Tavily rate limiting (see above)
2. Founder names incomplete/incorrect in source data
3. LinkedIn profiles don't exist or are private

**Solution**:
- Check data quality with: `python src/verify_quality.py`
- Review checkpoint file for status codes
- Adjust name matching strictness if needed

## Resuming After Interruption

The pipeline uses checkpoints stored in `data/checkpoints/hybrid_final_checkpoint.json`.

If interrupted:
1. Simply rerun the same command
2. It will skip already-processed items
3. Progress is saved after every batch

No data is lost!

## Verifying Data Quality

Run quality checks:
```bash
python src/verify_quality.py
```

**Output:**
- LinkedIn URL quality score
- Name matching accuracy
- Suspicious URLs for review

## Cost Estimation

### Tavily AI Search
- **Founder Discovery**: ~1,000 searches × $0.005 = ~$5
- **LinkedIn URL Finding**: ~1,000 searches × $0.005 = ~$5
- **Total**: ~$10 per full run

### Bright Data
- **LinkedIn Enrichment**: ~6,000 profiles × $0.01 = ~$60
- **Total**: ~$60 per full run

**Total Pipeline Cost**: ~$70 for complete run

## Advanced Configuration

### Batch Size Tuning

Adjust batch sizes for rate limit management:

```bash
# Smaller batches (slower but safer)
python src/2_find_founders.py --batch 50

# Larger batches (faster but may hit limits)
python src/2_find_founders.py --batch 500
```

### Filtering by Location

To target different cities, edit the Austin detection logic in scripts:

```python
# Current (Austin):
is_austin = any(kw in location.lower() for kw in ['austin', 'atx'])

# For San Francisco:
is_target = any(kw in location.lower() for kw in ['san francisco', 'sf', 'bay area'])
```

## Getting Help

1. Check [METHODOLOGY.md](METHODOLOGY.md) for technical details
2. Check [ARCHITECTURE.md](ARCHITECTURE.md) for system design
3. Review checkpoint file for detailed status
4. Check API provider status pages
5. Open an issue with error logs

---

**Next Steps**: See [USE_CASES.md](USE_CASES.md) for recruiting applications
