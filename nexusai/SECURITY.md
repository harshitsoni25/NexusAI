# Security Policy

## Supported Versions

| Version | Supported |
|---|---|
| 0.1.x | :white_check_mark: |
| < 0.1 | :x: |

## Reporting a Vulnerability

**Please do not open a public issue for security problems.**

Email **security@nexusai.example** with a description and impact, reproduction steps or
a proof of concept, affected components and versions, and any suggested remediation.

You can expect an acknowledgement within **2 business days**, an initial assessment within
**5 business days**, and coordinated disclosure once a fix is available.

## Hardening

Nexus AI is built with security in mind: a hardened Electron shell, scrypt password
hashing, stateless signed tokens, hashed API keys, role-based access control, and a full
audit trail. See the [configuration reference](https://nexusai.github.io/nexusai/api/configuration/) for operational
hardening guidance.
