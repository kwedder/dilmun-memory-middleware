---
episode: point2cad-integration-plan
scope: cad-research
tags: [point2cad, integration, plan, faster-pipeline]
created: 2026-06-14
status: planning
---

# Episode: Point2CAD Integration Plan

## Context
Research showed Point2CAD is faster than Scan2CAD for 3D scan to CAD conversion.

## Key Findings

### Point2CAD Advantages
- No training required (uses pretrained models)
- Docker deployment: `docker run -it --rm -v .:/work/point2cad toshas/point2cad:v1 python -m point2cad.main`
- Parallel surface fitting with multiprocessing
- <5 min runtime on single model (GPU)
- CVPR 2024 (newer than Scan2CAD's 2019)

### Scan2CAD Disadvantages
- Requires training phase
- Complex multi-step pipeline
- Longer setup time

## Integration Architecture
```
3D Scan (RGB-D/Point Cloud)
    ↓
Point2CAD (Dockerized)
    ↓
Initial CAD Model (PLY/JSON topology)
    ↓
text-to-cad (Optimization Layer)
    ↓
Text-Guided Refinement
    ↓
Final CAD (STEP)
```

## Next Steps
1. Test Point2CAD with sample data
2. Parse output (PLY meshes, topology JSON)
3. Integrate with text-to-cad pipeline
4. Build unified pipeline script

## Dilmun State
- Fact: `point2cad-vs-scan2cad-comparison.md`
- Status: Planning for implementation
