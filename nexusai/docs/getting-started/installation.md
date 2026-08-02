# Installation

Nexus AI runs as a command-line tool and library, and ships a set of applications
around it. Choose the path that fits you.

## Requirements

- **Python** 3.12 or newer (engine, API, scheduler, plugins, enterprise)
- **Node** 22+ and **npm** 10+ (web, reporting, desktop)

## Install the engine

=== "From source (editable)"

    ```bash
    git clone https://github.com/nexusai/nexusai
    cd nexusai
    pip install -e ".[dev]"
    nexusai doctor        # verify the installation
    ```

=== "Runtime only"

    ```bash
    pip install -e .
    nexusai version
    ```

The engine ships a minimal runtime by design. Optional extras (for example additional
export formats) are installed on demand:

```bash
pip install -e ".[visual]"     # example optional extra
```

## Install the applications

Each application under `pro/` installs independently.

```bash
pip install -e pro/api               # REST API
pip install -e pro/scheduler         # scheduler
pip install -e pro/plugins           # plugin manager
pip install -e "pro/enterprise[api]" # enterprise (with the optional REST service)

(cd pro/web && npm ci)               # web UI
(cd pro/reporting && npm ci)         # reporting UI
(cd pro/desktop && npm ci)           # desktop shell
```

## Desktop application

Prebuilt desktop installers are published for each platform on the Releases page:

- **Windows** — run the NSIS `Setup` installer.
- **macOS** — open the `.dmg` and drag the app to Applications.
- **Linux** — the `.AppImage` (make it executable), or the `.deb` / `.rpm` package.

See [Deployment → Desktop](../deployment/desktop.md) for details.

## Verify

```bash
nexusai doctor            # required checks should report PASS
nexusai version           # prints the version
```

Next: the [Quickstart](quickstart.md).
