# Phase 1 Plan: Fix Dependencies

## Tasks

### 1.1 Verify Python Environment

- [x] Check Python version compatibility
- [x] Verify pip is working
- [x] Confirm dilmun-memory-middleware package is importable

### 1.2 Install Missing Dependencies

- [x] Install `python-dotenv`
- [x] Install `requests`

### 1.3 Fix Script Imports

- [x] Update `middleware_server.py` with correct path
- [x] Update `write_project.py` with correct path
- [x] Update `check_index.py` with correct path
- [x] Update `active_check.py` with correct path
- [x] Update `shopify_auth.py` with correct paths

### 1.4 Verify Fixes

- [x] Run middleware_server.py without errors
- [x] Run check_index.py without errors
- [x] Run active_check.py without errors

## Verification Criteria

- All scripts import successfully
- All scripts can read from `/home/kworqs/.pi/subdilmun`
- No ModuleNotFoundError or FileNotFoundError

---
*Phase 1 completed: 2026-06-19*
