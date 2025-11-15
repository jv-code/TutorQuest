# Setup Scripts

This folder contains setup scripts for initializing infrastructure and dependencies.

## Daytona Snapshot Creation

### `create_manim_snapshot.py`

Creates a Daytona snapshot with Manim and manim-voiceover pre-installed for fast video generation.

**Current snapshot:** `manim-voiceover-v4`

**Resources:**
- 2 vCPU
- 4 GiB RAM
- 8 GiB Disk

**Included packages:**
- Python 3.12 (Debian Slim)
- System: ffmpeg, libcairo2-dev, libpango1.0-dev, sox, libsox-fmt-all
- Python: setuptools, manim, manim-voiceover[gtts]

**Usage:**
```bash
cd backend
source .venv/bin/activate
python setup/create_manim_snapshot.py
```

**Note:** Building the snapshot takes ~10-15 minutes. After creation, update `src/services/video.py` with the new snapshot name if changed.

## Adding New Setup Scripts

When adding new setup scripts:
1. Place them in this `setup/` folder
2. Document their purpose in this README
3. Include clear usage instructions
