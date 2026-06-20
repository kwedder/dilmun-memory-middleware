---
scope: cad-research
entity: text-to-cad-pipeline
status: complete
timestamp: 2026-06-14
tags: [research, cad, 3d-scan, text-to-model, pipeline]
---

# Text-to-CAD Pipeline Research

## Goal
Create a program that takes 3D scans → makes them 3D models → optimizes based on text input

## Tools Identified

### 1. Scan2CAD (skanti/Scan2CAD)
- **Purpose**: 3D scan to CAD model alignment
- **Paper**: CVPR 2019 Oral presentation
- **Approach**: 
  - Deep learning for aligning CAD models from database to 3D scans
  - Uses keypoint correspondences between scan and CAD
  - Input: RGB-D scans (ScanNet) + CAD database (ShapeNet)
  - Output: Aligned CAD models with transformations
- **Key Features**:
  - 97,607 keypoint correspondences
  - 14,225 objects aligned
  - 1,506 scans processed
- **Workflow**:
  1. Process scans as SDF voxel grids
  2. Process CADs as DF voxel grids
  3. Train PyTorch for heatmap prediction
  4. Run alignment algorithm (9DoF)
  5. Output: Aligned CAD models

### 2. text-to-cad (earthtojake/text-to-cad)
- **Purpose**: Agent skills for CAD generation from text
- **Approach**: 
  - AI agent skills library for CAD, robotics, hardware design
  - Plain-language text to CAD models
  - Uses build123d + OCP (OpenCASCADE)
- **Key Features**:
  - STEP, STL, 3MF, GLB export
  - CAD Viewer for browser previews
  - Robot description (URDF, SRDF, SDF)
  - Benchmark with 10 example prompts
- **Output Formats**: STEP (primary), STL, 3MF, GLB

## Pipeline Architecture (Recommended)

```
3D Scan (RGB-D/Point Cloud)
    ↓
Point2CAD (Faster: CVPR 2024, Dockerized)
    ↓
Initial CAD Model
    ↓
text-to-cad Optimization
    ↓
Text-Guided Refinement
    ↓
Final CAD Model (STEP/STL)
```

## Updated Recommendation
**Point2CAD** (CVPR 2024) is faster and more practical than Scan2CAD:
- No training required (uses pretrained models)
- Docker deployment
- <5 min runtime
- Parallel surface fitting

## Next Steps
1. Test Point2CAD with sample data
2. Parse output (PLY meshes, topology JSON)
3. Integrate with text-to-cad pipeline
4. Build unified pipeline script

## Implementation Status

### Pipeline Script Created
- **Location**: `/home/kworqs/apps/cad-pipeline/pipeline.py`
- **Features**:
  - Dependency checking (Docker/PyTorch)
  - Point2CAD execution
  - Output parsing (PLY, topology JSON)
  - Text-to-cad prompt generation

### Dependencies Status
- **Docker**: ❌ Not available
- **PyTorch**: ❌ Not available
- **Point2CAD**: Cannot run locally

### Alternative Options
1. **Google Colab**: [Point2CAD Colab](https://colab.research.google.com/drive/1o5nNmu1CIn7I5wFFmF8-u7O66Bxqt_xC)
2. **Docker Install**: `curl -fsSL https://get.docker.com | sh`
3. **PyTorch Install**: `pip3 install torch --index-url https://download.pytorch.org/whl/cpu`

### Next Steps
1. Install Docker or PyTorch
2. Run pipeline: `python3 pipeline.py --input sample.xyzc --output ./output --text-prompt "optimize for 3D printing"`
3. Integrate with text-to-cad CLI for optimization
