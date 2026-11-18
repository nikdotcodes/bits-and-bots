# Bits and Bots

## Run locally

```sh
uv run bits-and-bots
```

The app listens on `http://127.0.0.1:8000`. Configure optional settings with
environment variables: `SECRET_KEY`, `DB_PATH`, `BASE_URL`.

Run the test suite with `make test`.

## Application layout

- `src/bits_and_bots/main.py` creates the FastAPI app and mounts the routers.
- `src/bits_and_bots/routers/` contains authentication, public, and volunteer routes.
- `src/bits_and_bots/templates.py` configures the filesystem-backed Jinja loader.
- `src/bits_and_bots/web_templates/` contains the Jinja page, base, and macro templates.
- `src/bits_and_bots/static/styles.css` contains the shared theme.
- `src/bits_and_bots/database.py`, `security.py`, and `config.py` contain persistence,
  session security, and configuration.
