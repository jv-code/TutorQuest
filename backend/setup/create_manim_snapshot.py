from daytona import Daytona, DaytonaConfig, Image, CreateSnapshotParams
from src.config import settings

def create_snapshot():
    config = DaytonaConfig(
        api_key=settings.daytona_api_key,
        api_url=settings.daytona_api_url
    )
    daytona = Daytona(config)

    snapshot_name = "manim-voiceover-v4"

    print(f"Creating '{snapshot_name}' with 2vCPU / 4GiB / 8GiB\n")

    image = (
        Image.debian_slim("3.12")
        .run_commands(
            "apt-get update",
            "apt-get install -y ffmpeg libcairo2-dev libpango1.0-dev sox libsox-fmt-all"
        )
        .pip_install("setuptools", "manim", "manim-voiceover[gtts]")
        .workdir("/home/daytona")
    )

    daytona.snapshot.create(
        CreateSnapshotParams(
            name=snapshot_name,
            image=image,
            vcpu=2,
            memory_mb=4096,
            disk_gb=8
        ),
        on_logs=print,
    )

    print("\n" + "="*60)
    print(f"SUCCESS! '{snapshot_name}' created!")
    print("Resources: 2vCPU / 4GiB / 8GiB")
    print("\nUpdate backend/src/services/video.py line 74:")
    print(f'  snapshot="{snapshot_name}"')
    print("="*60)

if __name__ == "__main__":
    create_snapshot()
