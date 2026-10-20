# System Bus Design Diagrams

This directory contains the main architecture and behavioral diagrams for the shared-memory system bus design.

## Included diagrams

- [system-bus-architecture.svg](system-bus-architecture.svg) — top-level block diagram
- [memory-map.svg](memory-map.svg) — address map and slave selection
- [transaction-timing.svg](transaction-timing.svg) — master request / grant / transaction / ack timing
- [arbiter-timing.svg](arbiter-timing.svg) — grant release and fixed-priority arbitration
- [read-write-flow.svg](read-write-flow.svg) — read and write data flow
- [control-fsm.svg](control-fsm.svg) — control-flow / state-machine view

These diagrams correspond to the implementation in `amaranth_bus.py` and the generated Verilog in `system_bus.v`.
