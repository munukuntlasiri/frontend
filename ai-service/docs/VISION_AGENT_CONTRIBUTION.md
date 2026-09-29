# Vision Agent Contribution

## Contributor
**Name:** Bhuvana Kruthi  
**Role:** Vision Agent / Civic Issue Image Classification

## Overview

This contribution focuses on the image-analysis component of CivicResolve-AI.
The Vision Agent analyzes uploaded civic-issue images and maps them to the
project's supported civic issue taxonomy.

## Technical Implementation

- Implemented and tested the Vision Agent workflow.
- Used `google/siglip-base-patch16-224` for local zero-shot image classification.
- Implemented prompt-based civic issue classification.
- Maintained taxonomy mapping between detected categories and civic issues.
- Used relative zero-shot prompt scores for classification.
- Implemented conservative detection gates to reject ambiguous classifications.

## Supported Civic Issues Tested

- Pothole
- Cracked Road
- Damaged Pavement
- Broken Footpath
- Garbage Accumulation
- Overflowing Bin
- Illegal Dumping
- Water Leakage
- Drainage Overflow
- Waterlogging
- Open Drain
- Broken Streetlight
- Damaged Public Infrastructure
- Broken Traffic-related Infrastructure

## Classification Output

The Vision Agent returns information including:

- Detection status
- Category
- Issue
- Taxonomy category
- Taxonomy issue
- Relative score
- Provider
- Model
- Image dimensions
- Ranked predictions
- Detection reasons
- Model limitations

## Detection Gates

The MVP currently uses:

- Minimum civic score: `0.20`
- Minimum control margin: `0.10`
- Minimum runner-up margin: `0.10`

These conservative gates help reject ambiguous predictions rather than
forcing a classification.

## Prompt Calibration

Prompt groups were refined to improve separation between visually similar
civic issues.

Examples include:

- Pothole vs. Cracked Road vs. Damaged Pavement
- Garbage Accumulation vs. Illegal Dumping vs. Overflowing Bin
- Open Drain vs. Drainage Overflow vs. Waterlogging

The calibration focused on improving semantic distinction without lowering
the global detection thresholds.

## Validation

Manual representative-image testing was performed across the supported
civic issue categories.

A clean-road control image was also tested to verify that images without
a civic issue can be rejected correctly.

Final automated test result:

`60 passed, 3 subtests passed`

## Current Model

- Provider: `siglip_local`
- Model: `google/siglip-base-patch16-224`
- Inference device used during testing: CPU
- Classification approach: zero-shot prompt-based image classification

## Known Limitations

- SigLIP is a general zero-shot vision-language model rather than a
  municipal defect detector.
- Relative scores are not calibrated probabilities.
- Similar visual subclasses can still overlap.
- Current classification evaluates the whole image.
- Bounding-box localization is not currently implemented.
- Representative real-world validation should be expanded before
  production deployment.

## Files Worked On

Primary files involved in this contribution include:

- `app/agents/vision_agent.py`
- `tests/test_vision_agent.py`
- `docs/API_CONTRACT.md`
- `README.md`

## Final Status

Vision Agent implementation and focused taxonomy calibration are complete
for the current hackathon MVP.

Automated verification:

**60 tests passed + 3 subtests passed.**