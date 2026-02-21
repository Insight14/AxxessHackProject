#!/usr/bin/env python3
"""
One-time script to create the TwelveLabs index for healthcare conversations.
Run from the project root:  python scripts/setup_index.py

After running, copy the printed INDEX_ID into your backend/.env file as:
  TWELVELABS_INDEX_ID=<id>
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from services.twelvelabs_client import TwelveLabsClient


async def main():
    client = TwelveLabsClient()
    print("Creating TwelveLabs index...")
    result = await client.create_index("healthcare-conversations")
    index_id = result.get("_id")
    print(f"\nIndex created successfully!")
    print(f"INDEX_ID: {index_id}")
    print(f"\nAdd this to backend/.env:")
    print(f"TWELVELABS_INDEX_ID={index_id}")

    # Auto-write to .env if it exists or create it
    env_path = os.path.join(os.path.dirname(__file__), "..", "backend", ".env")
    lines = []
    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = [l for l in f.readlines() if not l.startswith("TWELVELABS_INDEX_ID=")]
    lines.append(f"TWELVELABS_INDEX_ID={index_id}\n")
    with open(env_path, "w") as f:
        f.writelines(lines)
    print(f"\nAuto-written to {env_path}")


if __name__ == "__main__":
    asyncio.run(main())
