# ADR-0006: Root-24 Architecture, Token, DAO Documentation + CSP

## Status
Accepted

## Context
The SSID documentation site needs comprehensive coverage of the Root-24 architecture,
token economics, and DAO governance model. Additionally, Content Security Policy (CSP)
headers need to be configured for the documentation site.

## Decision
- Add Root-24 architecture documentation pages
- Add token economics and DAO governance documentation
- Configure CSP headers in the Astro build pipeline

## Consequences
- Documentation site covers all 24 canonical roots
- Token/DAO docs are publicly accessible (no secrets)
- CSP headers improve security posture of the docs site
