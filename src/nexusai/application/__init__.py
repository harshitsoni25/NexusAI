"""Use cases and orchestration.

This layer sequences domain policy and port calls. It owns *orchestration* --
the order of operations, concurrency, error recovery, transaction scope -- and
contains no domain decisions. A useful review heuristic: if a line in this layer
contains a threshold, a weight or a business constant, it belongs in
``domain.policy`` instead.

Depends on ``domain`` and ``shared`` only. It names ports; it never names
adapters.
"""

from __future__ import annotations
