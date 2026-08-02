"""One module per use case, each a single entry point into the framework.

Introduced by the phases that own each workflow: analyse site, execute scrape
job, validate run, assess quality, detect changes, export dataset, generate
report, resume job.
"""

from __future__ import annotations
