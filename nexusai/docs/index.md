---
hide:
  - navigation
  - toc
---

<div class="hk-hero" markdown>
<img class="hk-hero__logo" src="assets/images/logo.svg" alt="Nexus AI" />
<div class="hk-hero__title">Nexus AI</div>
<p class="hk-hero__tagline">
A certified, plugin-driven web-scraping platform — a clean scraping engine plus a REST
API, web and desktop apps, a scheduler, plugin management, analytics, and multi-tenant
enterprise features.
</p>

<div class="hk-pills">
  <span class="hk-pill">Plugin-driven engine</span>
  <span class="hk-pill">CLI &amp; REST API</span>
  <span class="hk-pill">Web &amp; desktop apps</span>
  <span class="hk-pill">Scheduler</span>
  <span class="hk-pill">Reporting</span>
  <span class="hk-pill">Enterprise tenancy</span>
  <span class="hk-pill">C1–C4 certified</span>
</div>

<div class="hk-hero__cta" markdown>
[Get started :material-rocket-launch:](getting-started/installation.md){ .md-button .md-button--primary }
[Architecture :material-sitemap:](architecture/overview.md){ .md-button }
[View on GitHub :fontawesome-brands-github:](https://github.com/nexusai/nexusai){ .md-button }
</div>
</div>

---

## Explore

<div class="grid cards" markdown>

-   :material-download:{ .lg .middle } **Getting Started**

    ---

    Install Nexus AI and run your first scrape from the CLI or the UI.

    [:octicons-arrow-right-24: Installation & quickstart](getting-started/installation.md)

-   :material-sitemap:{ .lg .middle } **Architecture**

    ---

    How the engine and applications fit together — composition, request lifecycle,
    scheduler, plugins and reporting, with diagrams.

    [:octicons-arrow-right-24: Architecture](architecture/overview.md)

-   :material-puzzle:{ .lg .middle } **Plugins**

    ---

    Extend Nexus AI through ten published extension points discovered from installed
    distributions.

    [:octicons-arrow-right-24: Build a plugin](plugins/plugin-development.md)

-   :material-console:{ .lg .middle } **API & CLI**

    ---

    The command-line interface, configuration reference, and every supported environment
    variable.

    [:octicons-arrow-right-24: CLI reference](api/cli.md)

-   :material-cloud-upload:{ .lg .middle } **Deployment**

    ---

    Run in Docker, package the desktop app, and cut releases.

    [:octicons-arrow-right-24: Deploy](deployment/docker.md)

-   :material-check-decagram:{ .lg .middle } **Quality**

    ---

    The testing strategy, CI/CD pipelines, and the final C1–C4 certification results.

    [:octicons-arrow-right-24: Quality & certification](quality/certification.md)

</div>

## Why Nexus AI

!!! success "Certified engine, reused unchanged"
    The scraping engine passes C1–C4 certification and is frozen. Every application reuses
    it as a library, so new capabilities never put the certified core at risk.

<div class="grid cards" markdown>

-   :material-layers-triple:{ .lg .middle } **Clean architecture**

    ---

    Domain, application and infrastructure are separated behind ports; a composition root
    wires everything explicitly.

-   :material-cloud-cog:{ .lg .middle } **Cloud-ready**

    ---

    Stateless auth, pluggable persistence, and 12-factor configuration for horizontal
    scaling.

-   :material-lock-check:{ .lg .middle } **Secure by default**

    ---

    Hardened desktop shell, scrypt hashing, signed tokens, hashed API keys, RBAC and audit
    logging.

-   :material-poll:{ .lg .middle } **Observable**

    ---

    Correlated structured logs, health and doctor checks, analytics, and native crash
    reporting.

</div>
