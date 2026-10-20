# System Bus Architecture

This repository implements a shared-memory system bus for a simple digital design assignment. The design contains two masters, a fixed-priority arbiter, a shared data/address bus, an address decoder, and three memory-mapped slave regions. The implementation is written in Amaranth HDL and also exported to synthesizable Verilog.

The project is designed to model a hardware bus architecture similar to a small embedded SoC interconnect, with:

- two requesters (masters)
- one shared bus
- three address-mapped slave blocks
- fixed-priority arbitration (Master 0 has higher priority than Master 1)
- read/write transactions with acknowledgement and error signaling

## Project purpose

This assignment focuses on:

- bus arbitration and grant control
- memory-mapped address decoding
- slave selection and data routing
- write/read transactions with bus-level handshake behavior
- simulation-based verification and waveform generation
- exporting the design into Verilog for downstream FPGA/ASIC flow compatibility

## Bus architecture summary

The top-level structure is:

- Master 0
- Master 1
- Arbiter
- Shared bus mux
- Address decoder
- Slave 0 (4 KB)
- Slave 1 (4 KB)
- Slave 2 (2 KB)
- Response path (`ack`, `rdata`, `err`)

The architecture is essentially:

```text
Master 0 ─┐
          ├─> Arbiter ─> Shared bus ─> Address Decoder ─> Slave 0 / Slave 1 / Slave 2
Master 1 ─┘                                              │
                                                        └─> Response: rdata + ack + err
```

## Address map

The system uses a 14-bit address bus and 8-bit data bus.

- `0x0000 - 0x0FFF` → Slave 0 (4 KB)
- `0x1000 - 0x1FFF` → Slave 1 (4 KB)
- `0x2000 - 0x27FF` → Slave 2 (2 KB)
- any other address → unmapped; `err` is asserted and the bus responds with `ack`

## Signal behavior

Each master drives the following interface signals:

- `req` — request to use the bus
- `we` — write enable
- `addr` — address for the transaction
- `wdata` — write data

The bus returns:

- `gnt` — grant signal for the current master
- `ack` — transaction completion/handshake signal
- `rdata` — read data returned from the selected slave
- `err` — set when an unmapped address is accessed

## Arbitration policy

The arbiter is a fixed-priority controller:

- `M0` has priority over `M1`
- no pre-emption occurs once a master is granted the bus
- the grant is released when the acknowledged transfer completes
- after release, the next request can be serviced

This is implemented in the `Arbiter` block in `amaranth_bus.py`.

## Slave model

The system includes three memory-mapped RAM slaves:

- each slave is a small synchronous RAM block
- a write operation stores to memory
- a read operation returns the previously stored value
- the read data is valid alongside the acknowledgement signal
- each access is acknowledged in a one-cycle pulse-like handshake pattern

## Error handling

If the address is outside the valid ranges:

- no slave is selected
- `unmapped` is asserted in the decoder
- the bus raises `err = 1`
- the transaction still completes with `ack = 1`

This makes the design robust for invalid memory access patterns and helps verify bus correctness in simulation.

## Design files

### Source implementation

- `amaranth_bus.py` — main Amaranth HDL implementation of the system bus
- `system_bus.v` — generated Verilog export from the Amaranth design

### Documentation and diagrams

- `ARCHITECTURE.md` — architecture description and data flow summary
- `DIAGRAMS.md` — list of generated diagrams
- `system-bus-architecture.svg` — top-level block diagram
- `memory-map.svg` — memory map and decoder view
- `transaction-timing.svg` — request/grant/ack timing overview
- `arbiter-timing.svg` — arbiter timing illustration
- `read-write-flow.svg` — read and write flow diagram
- `control-fsm.svg` — controller state view

### Additional artifact files

- `EN5102-AssignSysBus.pdf` — assignment specification or reference material
- `out/` — generated simulation outputs and exported Verilog artifacts
- `two_masters.vcd` — waveform capture for the two-master testbench

## Simulation and verification

The project includes self-checking verification routines in `amaranth_bus.py`.

Running the Python file executes the following checks:

1. Arbiter behavior tests
2. Address decoder tests
3. Reset behavior tests
4. Idle-state tests
5. Single-master transaction tests
6. Two-master arbitration tests
7. Verilog export

The tests validate:

- correct grant selection
- fixed-priority arbitration rules
- correct address decoding
- proper read-after-write behavior
- correct unmapped address handling
- correct operation under reset conditions

## Running the design

### Prerequisites

Install Python and the Amaranth HDL package:

```bash
python3 -m pip install amaranth
```

### Execute the project

From the repository root:

```bash
python3 amaranth_bus.py
```

This script will:

- run the testbench suite
- generate VCD waveforms in the `out/` directory
- export the module as Verilog into `out/system_bus.v`

## Output directory

The `out/` directory contains generated waveform and Verilog artifacts used for verification and implementation export.

## Implementation notes

This is a synthesizable hardware model written in Amaranth, which means the same Python description can be:

- simulated for behavioral validation
- converted to Verilog for FPGA or ASIC toolchains
- used as a structured hardware design reference

The design intentionally keeps the bus simple and explicit so that the bus protocol, memory map, arbitration behavior, and error handling can be followed easily.

## Typical use case

This implementation is suitable for learning and demonstrating:

- memory-mapped bus arbitration
- slave selection logic
- interconnect design patterns
- HDL simulation and verification workflow
- hardware-software architecture concepts for shared buses

## Repository status

This repository is a compact HDL project demonstrating a practical digital system bus design, with both modeling and verification included in the same source tree.

## License and usage

This project is provided as an academic/design assignment artifact. Use it for study, demonstration, and learning about bus architecture, arbitration, and HDL design.

## Quick summary

If you need the shortest description of the repository: it is an Amaranth-based two-master, three-slave shared-memory bus architecture with fixed-priority arbitration, 14-bit address decoding, 8-bit data transfers, acknowledgment signaling, and unmapped-address error handling.

---

For more detail on the block-level organization, see `ARCHITECTURE.md` and `DIAGRAMS.md`.
