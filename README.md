# Autonomous AI Operational Agent: Middle-Office Exception Triage & SQL Repair

An intelligent operational governance pipeline engineered in Python 3.12 that mimics human-in-the-loop exception handling. The agent ingests broken or non-compliant counterparty broker payloads, diagnoses data anomalies, queries system reference data via Model Context Protocol (MCP) tool design patterns, and automatically constructs exact SQL transaction patches.

## Operational & Architectural Blueprint
* **Ingestion Triage Engine:** Parses high-volume trade metadata vectors to catch downstream transmission breaks, mismatched schema formats, or data integrity violations.
* **Model Context Protocol (MCP) Simulation:** Emulates decoupling agentic logic from internal data silos, querying isolated system master registries (Counterparty LEI Maps, Valid Currency Tables, and Security Masters) to fetch real-time ground truth.
* **Deterministic SQL Patch Compiler:** Generates auditable, timestamped SQL transaction updates dynamically to modify the ledger state, shifting operational status back to Straight-Through Processing (STP) readiness without manual business analyst intervention.

## Core Engineering & Standards
* **Idempotent Operational Status Controls:** Explicitly injects tracking lineage (`last_modified_by = 'AI_OPERATIONAL_AGENT'`) into database outputs to maintain strict corporate audit controls.
* **Decoupled Architecture:** Designed to seamlessly sit behind enterprise API message queues (Kafka, RabbitMQ) or directly bridge AI orchestrator frameworks to corporate relational databases.
