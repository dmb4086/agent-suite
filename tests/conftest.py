import os

# Force tests onto sqlite before app modules import settings/engine.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
