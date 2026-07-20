# Data Enrichment Log

## Overview

Five records were added to improve the representation of access,
usage, merchant acceptance, deeper financial-service use, and policy
interventions.

## ENR_OBS_001 — Telebirr Agent Network Size

- Record type: observation
- Pillar: ACCESS
- Value: 320,300
- Observation date: 2025-06-30
- Source: Ethio Telecom 2024/25 Annual Performance Report
- Confidence: High
- Transformation: Converted 320.3 thousand to 320,300
- Relevance: Agent availability supports cash-in and cash-out access.

## ENR_OBS_002 — Telebirr Merchant Network Size

- Record type: observation
- Pillar: USAGE
- Value: 310,100
- Observation date: 2025-06-30
- Source: Ethio Telecom 2024/25 Annual Performance Report
- Confidence: High
- Transformation: Converted 310.1 thousand to 310,100
- Relevance: Merchant acceptance enables practical digital-payment use.

## ENR_OBS_003 — Telebirr Digital Savings Customers

- Record type: observation
- Pillar: USAGE
- Value: 1,770,000
- Observation date: 2025-06-30
- Source: Ethio Telecom 2024/25 Annual Performance Report
- Confidence: High
- Relevance: Measures deeper financial-service usage beyond registration.

## ENR_EVT_001 — National Digital Payments Strategy Phase Two

- Record type: event
- Category: policy
- Event date: 2025-03-28
- Source: National Bank of Ethiopia
- Confidence: High
- Relevance: Focuses on payment usage, interoperability, digital ID,
  financial inclusion, and merchant acceptance.
- Pillar: Left empty because events remain neutral.

## ENR_IMP_001 — NDPS Phase Two to Digital-Payment Usage

- Record type: impact_link
- Parent event: ENR_EVT_001
- Pillar: USAGE
- Related indicator: USG_DIGITAL_PAYMENT
- Direction: Increase
- Magnitude: Medium
- Estimated lag: 12 months
- Evidence basis: Theoretical
- Confidence: Medium
- Limitation: The direction is source-supported, but magnitude and lag
  are modeling assumptions requiring validation.