---
scope: cad-research
entity: point2cad-scan2cad-comparison
status: complete
timestamp: 2026-06-14
tags: [comparison, point2cad, scan2cad, performance]
---

# Point2CAD vs Scan2CAD Comparison

## Architecture Differences

### Scan2CAD (2019)
- **Type**: Neural network heatmap prediction
- **Pipeline**: 
  1. Train PyTorch model on ScanNet + ShapeNet
  2. Generate heatmaps for keypoints
  3. Align CAD models via 9DoF transformation
- **Requirements**: Training data, training phase
- **Complexity**: High (multiple phases, training required)
- **Code**: `Network/pytorch/main.py`, `Routines/Script/Alignment9DoF.py`

### Point2CAD (2024)
- **Type**: Surface fitting with INR
- **Pipeline**:
  1. Segment point cloud (ParseNet)
  2. Fit surfaces using Implicit Neural Representations
  3. Extract edges and corners
- **Requirements**: Pretrained models only (no training)
- **Complexity**: Lower (direct inference)
- **Code**: `point2cad/main.py`, `point2cad/fitting_one_surface.py`
- **Deployment**: Docker-based

## Speed Comparison

| Aspect | Scan2CAD | Point2CAD |
|--------|----------|-----------|
| Setup | Complex (train model) | Simple (docker run) |
| Runtime | ~GPU hours (training) | <5 min (inference) |
| Parallel | Limited | Yes (multiprocessing) |
| Dependencies | PyTorch, custom | Docker, ParseNet |

## Recommendation

**Point2CAD is faster and more practical** for the user's pipeline because:
1. No training required - uses pretrained models
2. Docker deployment simplifies setup
3. Parallel surface fitting
4. More recent (2024 vs 2019)
5. Direct inference pipeline

## Integration Path
```
3D Scan 
    ↓
Point2CAD (dockerized inference)
    ↓
Initial CAD
    ↓
text-to-cad (optimization)
```
