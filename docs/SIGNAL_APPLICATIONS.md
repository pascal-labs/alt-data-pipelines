# Signal Applications

## Overview

This repository contains two production-grade alternative data pipelines: Yelp restaurant longevity analysis (5,897 restaurants across 50 states) and TechStars founder intelligence (126 Austin-based founders from 4,042 companies). Both pipelines were originally built for operational use cases -- credit risk assessment and talent acquisition -- but the data and methodology connect directly to prediction market signal generation.

The value is not just the data. It is demonstrating the ability to build production-grade alternative data infrastructure that feeds into event modeling.

---

## Restaurant Longevity Signals and Prediction Markets

### The Data

The Yelp pipeline extracts time-in-business data by scraping oldest review dates for 5,897 restaurants. Key finding: the **3-year survival mark shows a 69% closure risk reduction**, meaning restaurants that pass the 3-year threshold have fundamentally different survival dynamics than those below it.

### Signal Application: Restaurant and Food Industry Contracts

Platforms like Kalshi list contracts on restaurant industry outcomes: monthly restaurant openings, food price indices, regional economic health indicators. Restaurant longevity data provides a direct informational edge for these contracts:

- **Survival rate distributions by geography and cuisine type** inform contracts on restaurant industry health metrics. If the pipeline detects an abnormal closure spike in a specific metro area, that signals before official BLS data releases.
- **Time-in-business curves** provide base rates for contracts structured around "will X% of restaurants in region Y survive the next N months." The 3-year inflection point is a quantifiable structural break that most market participants do not have.
- **Seasonal closure patterns** extracted from the data (January and February show elevated closure rates across all regions) provide timing signals for industry health contracts.

### Alternative Credit Risk to Event Probability

The original use case -- assessing restaurant financing risk using Yelp longevity as an alternative credit signal -- is itself a probability estimation problem. "What is the probability that this restaurant will remain operational through the credit term?" is structurally identical to "What is the probability that this event contract resolves YES?"

The pipeline demonstrates the ability to source, extract, clean, and analyze alternative data for probability estimation. The domain (restaurants) is incidental. The methodology (systematic scraping, anti-detection engineering, statistical analysis of survival distributions) transfers to any alternative data source that informs event outcomes.

---

## Founder Intelligence Signals and Startup Outcome Contracts

### The Data

The TechStars pipeline identifies 7,642 founders across 4,042 accelerator companies, with 87.9% LinkedIn profile coverage and full location enrichment. The Austin subset (126 founders) demonstrates geographic concentration analysis at a level most market participants do not have access to.

### Signal Application: Startup and Venture Ecosystem Contracts

Prediction markets increasingly list contracts on startup ecosystem outcomes: funding round volumes, IPO activity, tech sector employment, and regional economic indicators. Founder intelligence data provides several edge sources:

- **Founder density by metro area** predicts startup formation rates. Austin's 2.04x concentration relative to population is a leading indicator for tech employment and venture activity contracts in that region.
- **Cohort analysis** (peak activity in 2019, 22.1% average YoY growth) provides trend signals for startup ecosystem health contracts.
- **LinkedIn enrichment** captures career transitions. A spike in founders moving from startups to established companies signals ecosystem cooling; the reverse signals heating. This is a leading indicator relative to official employment data.

### Intelligence Infrastructure

The pipeline's checkpoint/resume architecture and cost efficiency ($0.017/record, 99.7% cost savings vs. vendor alternatives) demonstrate the ability to build scalable intelligence infrastructure. At prediction market scale, the question is never "can you get one data point" but "can you systematically collect, update, and process thousands of data points at production quality and acceptable cost." This pipeline answers that question.

---

## The Pipeline as Methodology Demonstration

### Production-Grade Alt Data Engineering

Both pipelines demonstrate skills that are directly required for prediction market quantitative research:

**Anti-Detection and Resilience**
- Custom user-agents, natural scrolling patterns, random delays (Yelp pipeline)
- CAPTCHA handling for 200+ challenges without pipeline failure
- Checkpoint/resume architecture for fault tolerance (TechStars pipeline)

**Scale and Efficiency**
- 5,897 restaurants processed with 92% URL discovery rate and 88% extraction success
- 500-850 records/minute processing throughput
- Cost optimization: $0.017/record for LinkedIn enrichment

**Data Quality**
- Multi-phase extraction (fast API discovery followed by targeted deep scraping)
- Validation at every stage with quality metrics tracking
- Statistical analysis of output distributions (survival curves, geographic concentration tests)

### What Matters for a Trading Desk

A prediction market trading desk does not need restaurant longevity data or founder databases specifically. What it needs is someone who can:

1. Identify an alternative data source that provides informational edge
2. Build a production pipeline to systematically extract that data
3. Process and validate the data at scale with acceptable quality metrics
4. Connect the data to a probability estimation or signal generation framework
5. Maintain the pipeline as sources change (anti-detection, schema changes, rate limits)

Both pipelines in this repository demonstrate all five capabilities.

---

## Cross-Pollination with Other Portfolio Projects

These pipelines do not exist in isolation. They connect to the broader prediction market research portfolio:

```
alt-data-pipelines (this repo)
    |
    |-- Restaurant longevity signals
    |-- Founder intelligence signals
    |
    v
event-probability-models
    |
    |-- Ensemble models consuming alt data features
    |-- BTC price + tweet volume event probability
    |
    v
polymarket-sdk
    |
    |-- CLOB API execution layer
    |-- Order management and position tracking
```

**Data flow:** Alternative data pipelines generate features and signals. Event probability models consume those features alongside market data to produce probability estimates. The Polymarket SDK provides the execution layer to act on those estimates.

This three-layer architecture -- data collection, probability modeling, execution -- mirrors how a prediction market trading desk operates. The alt-data pipelines are the first layer: systematic, scalable, production-grade data infrastructure that feeds everything downstream.

---

## Summary

| Pipeline | Records | Key Finding | Prediction Market Application |
|----------|---------|-------------|-------------------------------|
| Yelp Restaurant Longevity | 5,897 restaurants | 3-year mark = 69% closure risk reduction | Restaurant/food industry contracts, survival base rates |
| TechStars Founder Intelligence | 7,642 founders (126 Austin) | Austin 2.04x founder concentration | Startup ecosystem contracts, regional economic indicators |

The signal is in the methodology as much as the data. Building these pipelines demonstrates the full alternative data lifecycle: source identification, extraction engineering, quality validation, and signal framing -- the exact workflow required to generate edge in prediction markets.
