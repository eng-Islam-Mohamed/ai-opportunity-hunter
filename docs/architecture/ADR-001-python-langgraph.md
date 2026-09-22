# ADR-001: Python services with LangGraph orchestration

## Status

Accepted (locked by product owner).

## Decision

FastAPI owns HTTP boundaries, Python domain services own business behavior, PostgreSQL owns durable product state, and LangGraph owns stateful workflow routing. Direct execution is the initial runtime. Celery/Redis is deferred until measured scaling requirements justify it.

## Consequences

Graph nodes remain thin, deterministic logic is independently testable, and no visual workflow runtime or duplicate Celery state machine is introduced.

