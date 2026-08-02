# Quickstart

Run your first scrape in a couple of minutes.

## From the command line

```bash
# 1. Confirm the installation is healthy
nexusai doctor

# 2. Scrape a page, exporting CSV and an HTML report
nexusai scrape https://example.com --export csv --report html

# 3. Inspect what happened
nexusai jobs        # list jobs and their state
nexusai stats       # aggregate statistics
```

Artefacts (datasets, exports, reports, logs and state) are written under the data root
(`./.nexusai` by default — see [Configuration](configuration.md)).

## From the API and web UI

=== "Start the API"

    ```bash
    uvicorn nexusai_pro_api.main:app --port 8000
    # interactive docs at http://127.0.0.1:8000/docs
    ```

=== "Start the web UI"

    ```bash
    cd pro/web && npm ci
    npm run dev        # http://localhost:5173
    ```

In the UI, open **New Job**, enter a target URL, choose export and report formats, and
start the scrape. Track it from **Job Progress** and browse results in **Dataset
Explorer**.

!!! tip "Mock mode"
    The web and reporting apps ship a mock mode (`VITE_USE_MOCKS=true`, the default) so you
    can explore every screen without a running backend.

## Next steps

- Learn the [core concepts](concepts.md).
- Read the [CLI reference](../api/cli.md).
- Extend Nexus AI with a [plugin](../plugins/plugin-development.md).
