#!/usr/bin/env python3
"""Migration script to add api_code to existing watchlist entries.

This script handles the transition from the old Asset model (without api_code)
to the new model (with api_code required).

Usage:
    python -m fcli.scripts.migrate_watchlist [--dry-run]
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fcli.core.config import symbol_registry
from fcli.core.storage import storage


async def migrate_watchlist(dry_run: bool = False):
    """Migrate existing watchlist entries to include api_code.

    Args:
        dry_run: If True, only print what would be changed without modifying
    """
    print("Loading watchlist...")
    assets = await storage.load()

    if not assets:
        print("No assets found in watchlist.")
        return

    print(f"Found {len(assets)} assets in watchlist")

    migrated_count = 0
    already_ok_count = 0
    error_count = 0

    for asset in assets:
        # Check if already has api_code
        if asset.api_code:
            print(f"  ✓ {asset.code}: already has api_code='{asset.api_code}'")
            already_ok_count += 1
            continue

        # Try to infer market and resolve api_code
        try:
            inferred_market = symbol_registry.infer_market(asset.code)
            api_code = symbol_registry.resolve_api_code(asset.code, inferred_market)

            print(f"  → {asset.code}: market={inferred_market.value}, api_code='{api_code}'")

            if not dry_run:
                # Update the asset
                asset.api_code = api_code
                # Note: The storage layer will need to support update operations
                # For now, we'll remove and re-add
                await storage.remove(asset.code)
                await storage.add(asset)

            migrated_count += 1
        except Exception as e:
            print(f"  ✗ {asset.code}: ERROR - {e}")
            error_count += 1

    print("\nMigration Summary:")
    print(f"  Already migrated: {already_ok_count}")
    print(f"  Newly migrated:   {migrated_count}")
    print(f"  Errors:           {error_count}")

    if dry_run:
        print("\n[DRY RUN] No changes were made. Run without --dry-run to apply changes.")


async def main():
    """Main entry point."""
    dry_run = "--dry-run" in sys.argv or "-n" in sys.argv

    if dry_run:
        print("=" * 60)
        print("DRY RUN MODE - No changes will be made")
        print("=" * 60)

    await migrate_watchlist(dry_run=dry_run)


if __name__ == "__main__":
    asyncio.run(main())
