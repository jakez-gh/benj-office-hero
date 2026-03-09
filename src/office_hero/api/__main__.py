"""Office Hero API entry point."""

if __name__ == "__main__":
    import uvicorn

    from office_hero.api import app

    uvicorn.run(app, host="127.0.0.1", port=8000)
