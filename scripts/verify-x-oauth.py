#!/usr/bin/env python3
"""Verify X OAuth 2.0 credentials against the token endpoint."""

import asyncio
import sys

from xautopilot.config import settings
from xautopilot.services.x_oauth_service import oauth_client_type, verify_oauth_credentials


async def main() -> int:
    print("X OAuth credential check")
    print(f"  mode:          {settings.x_api_mode}")
    print(f"  client type:   {oauth_client_type()}")
    print(f"  redirect_uri:  {settings.x_redirect_uri}")
    print(f"  client_id set: {bool(settings.x_client_id)}")
    print(f"  secret set:    {bool(settings.x_client_secret)}")
    print()

    error = await verify_oauth_credentials()
    if error:
        print("FAIL:", error)
        return 1

    print("OK: Credentials accepted by X token endpoint (invalid code expected next).")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
