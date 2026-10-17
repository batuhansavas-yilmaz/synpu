import os

PORT = int(os.environ.get("SYNPU_PORT", "8787"))
PUSH_INTERVAL_S = 0.5
FPS_STALE_S = 2.0
