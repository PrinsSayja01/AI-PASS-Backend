# AI-Pass Backend (Marketplace + Skills Runtime) — Handoff Package

This repo contains an MVP backend for AI-Pass Marketplace:
- Skills Runtime (10 skills)
- Role-based access control (admin / developer / tenant)
- Device-bound enforcement (Bearer + Device-Token)
- Workflow submission/approval pipeline
- Tenant install history + rollback + version locking
- RAG MVP (tenant-isolated FAISS + doc ACL)
- Audit logging + CI battle tests + dependency scan

## Quick Start

### 1) Setup venv + install deps
```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
