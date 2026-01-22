import sys
import asyncio
import uvicorn

if __name__ == "__main__":
    # CRITICAL: Fix for Python 3.13 on Windows - Must be set BEFORE uvicorn creates the loop
    # Playwright requires ProactorEventLoop for subprocess support, but Python 3.13 defaults to SelectorEventLoop
    if sys.platform == 'win32' and sys.version_info >= (3, 13):
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("✓ Applied WindowsProactorEventLoopPolicy for Playwright compatibility")
        except Exception as e:
            print(f"Failed to set event loop policy: {e}")

    # Run the application
    # using "app.main:app" string import allows reload=True to work
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
