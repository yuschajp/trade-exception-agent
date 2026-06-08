# Autonomous AI Operational Agent: Middle-Office Exception Triage & SQL Repair

An intelligent operational governance pipeline engineered in Python 3.12 that mimics human-in-the-loop exception handling. The agent ingests broken or non-compliant counterparty broker payloads, diagnoses data anomalies, queries system reference data via Model Context Protocol (MCP) tool design patterns, and automatically constructs exact SQL transaction patches.

## Operational & Architectural Blueprint
* **Ingestion Triage Engine:** Parses high-volume trade metadata vectors to catch downstream transmission breaks, mismatched schema formats, or data integrity violations.
* **Model Context Protocol (MCP) Simulation:** Emulates decoupling agentic logic from internal data silos, querying isolated system master registries (Counterparty LEI Maps, Valid Currency Tables, and Security Masters) to fetch real-time ground truth.
* **Deterministic SQL Patch Compiler:** Generates auditable, timestamped SQL transaction updates dynamically to modify the ledger state, shifting operational status back to Straight-Through Processing (STP) readiness without manual business analyst intervention.

## Core Engineering & Standards
* **Idempotent Operational Status Controls:** Explicitly injects tracking lineage (`last_modified_by = 'AI_OPERATIONAL_AGENT'`) into database outputs to maintain strict corporate audit controls.
* **Decoupled Architecture:** Designed to seamlessly sit behind enterprise API message queues (Kafka, RabbitMQ) or directly bridge AI orchestrator frameworks to corporate relational databases.

## 🏗️ System Architecture

```mermaid
graph TD
    %% Define Styles
    classDef broker fill:#f9f9f9,stroke:#333,stroke-width:1px;
    classDef agent fill:#e1f5fe,stroke:#0288d1,stroke-width:2px;
    classDef mcp fill:#fff3e0,stroke:#f57c00,stroke-width:1px;
    classDef db fill:#e8f5e9,stroke:#388e3c,stroke-width:2px;

    %% Workflow Nodes
    A[Broken Counterparty JSON Payload] --> B(triage_exception)
    
    subgraph "AI Exception Agent Pipeline"
        B --> C{Validate JSON Schema}
        C -- Malformed --> D[Status: REJECTED]
        C -- Valid JSON --> E{Check Currency & LEI}
        
        E --> F[Query MCP Reference Tools]
    end
    
    subgraph "Static Reference Data Layer (MCP)"
        F --> G[(VALID_CURRENCIES)]
        F --> H[(LEI_MAP)]
    end
    
    G --> I{Exception Detected?}
    H --> I
    
    I -- No Exceptions --> J[Status: STP_READY]
    I -- Data Break Found --> K(generate_sql_repair)
    
    subgraph "Automated Remediation"
        K --> L[Compile Dynamic SQL Patch]
        L --> M[Append 'AI_OPERATIONAL_AGENT' Audit Trail]
    end
    
    M --> N[(Target Database: trade_ledger)]

    %% Apply Styles
    class A broker;
    class B,C,E,I,K,L,M agent;
    class F,G,H mcp;
    class N db;
