# FAQ

??? question "Can I add capabilities without changing the engine?"
    Yes — that's the point of the plugin system. The engine publishes ten extension points
    and discovers implementations from installed distributions. See
    [Plugin Development](../plugins/plugin-development.md).

??? question "Can I run the web UI without a backend?"
    Yes. The web and reporting apps ship a mock mode (`VITE_USE_MOCKS=true`, the default),
    so every screen works without a running backend.

??? question "Where does Nexus AI write its data?"
    Under the data root, `./.nexusai` by default. Change it with
    `NEXUSAI_PATHS__ROOT`. See [Configuration](configuration.md).

??? question "Which export and report formats are supported?"
    CSV, JSON and NDJSON exports, and HTML and JSON reports, out of the box. Additional
    formats can be added through the exporter and report-generator extension points.

??? question "How do I resume an interrupted scrape?"
    Jobs are checkpointed. Run `nexusai resume <job-id>` (or use the API/UI) to continue
    from the last checkpoint.

??? question "Is there an interactive API reference?"
    Yes — start the API and open `/docs` for the OpenAPI UI.

??? question "Which platforms are supported?"
    The engine and Python services run anywhere Python 3.12+ runs. The desktop app targets
    Windows, macOS and Linux on x64 and arm64.
