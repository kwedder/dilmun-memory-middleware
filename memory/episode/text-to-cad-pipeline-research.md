---
episode: text-to-cad-pipeline-research
scope: cad-research
tags: [research, cad, 3d-scan, pipeline, text-to-model]
created: 2026-06-14
status: complete
---

# Episode: Text-to-CAD Pipeline Research

## Context
User wants to create a program that:
1. Takes 3D scans as input
2. Converts them to 3D models
3. Optimizes based on text input

## Research Actions

### Scan2CAD (skanti/Scan2CAD)
- CVPR 2019 paper for 3D scan to CAD alignment
- Aligns CAD models from ShapeNet database to ScanNet scans
- Uses keypoint correspondences
- Outputs aligned 3D models

### text-to-cad (earthtojake/text-to-cad)
- Agent skills library for text-to-CAD
- Plain language to CAD models
- STEP export primary, plus STL/3MF/GLB
- Uses build123d + OpenCASCADE

## Pipeline Architecture
```
3D Scan → Scan2CAD → Initial CAD → text-to-cad → Text-Guided Refinement → Final Model
```

## Next Actions
1. Set up Scan2CAD environment (PyTorch, ScanNet, ShapeNet)
2. Set up text-to-cad (Node/Python agent skills)
3. Develop integration layer for text-guided optimization
4. Create prototype pipeline

## Dilmun State
- Fact: `text-to-cad-pipeline-research.md`
- Status: Research complete, implementation pending
