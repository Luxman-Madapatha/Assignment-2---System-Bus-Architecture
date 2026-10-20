# System Bus Architecture

This repository contains an Amaranth HDL implementation of a small shared-memory system bus for a digital design assignment. The design models a two-master, three-slave bus with fixed-priority arbitration, address decoding, read/write memory access, and error signaling for unmapped addresses.

## Overview

The implementation in `amaranth_bus.py` builds a synthesizable bus structure with:

- 2 masters
- 1 shared bus interconnect
- 3 memory-mapped slave RAM blocks
- 1 fixed-priority arbiter
- 1 address decoder
- asynchronous reset and synchronous clock domain logic
- automatic Verilog export for downstream hardware flows

The bus operates on:

- 14-bit address bus
- 8-bit data bus
- fixed-priority arbitration where Master 0 has priority over Master 1

## Block-level architecture

```text
Master 0 ─┐
          ├─> Arbiter ─> Shared bus mux ─> Address decoder ─> Slave 0 / Slave 1 / Slave 2
Master 1 ─┘                                                 │
                                                            └─> Response: ack + rdata + err
```

The design consists of these implementation blocks:

- `Arbiter`: decides which master gets access to the shared bus
- `AddressDecoder`: decodes the 14-bit address and selects the appropriate slave
- `Slave`: memory-backed RAM slave with synchronous read/write behavior
- `SystemBus`: top-level interconnect that combines arbitration, muxing, selection, and response generation

## Address map and memory layout

The decoder checks the following mapped regions:

- `0x0000 - 0x0FFF` → Slave 0 (4 KB)
- `0x1000 - 0x1FFF` → Slave 1 (4 KB)
- `0x2000 - 0x27FF` → Slave 2 (2 KB)
- anything else → unmapped address

Slave 2 is smaller because it uses 11 address bits (`2 KB` range), while Slave 0 and Slave 1 use 12-bit addresses (`4 KB` each).

## Bus protocol

Each master presents the following signals:

- `req` — request to access the bus
- `we` — write enable
- `addr` — target address
- `wdata` — write data

The bus responds with:

- `gnt` — grant to the active master
- `ack` — transaction completion pulse/handshake
- `rdata` — data returned from the selected slave
- `err` — asserted for unmapped addresses

The actual transfer flow is:

1. A master asserts `req` and drives `we`, `addr`, and `wdata`
2. The arbiter grants the bus to one master using fixed priority
3. The granted master drives the shared bus signals
4. The decoder maps the address to a valid slave
5. The selected slave performs the read/write operation
6. The response path returns `ack`, `rdata`, and `err`

## Arbitration behavior

The arbiter is implemented as a fixed-priority controller:

- `M0` has higher priority than `M1`
- no pre-emption occurs once a master is granted the bus
- the grant is released after the current transfer is acknowledged
- if both masters request simultaneously, Master 0 wins

This behavior is enforced in `Arbiter.elaborate()` and validated by the self-checking tests in `amaranth_bus.py`.

## Error handling

If an access address does not match any valid slave region:

- the decoder sets `unmapped = 1`
- the bus asserts `err = 1`
- the transaction still completes with `ack = 1`

This allows invalid addresses to be detected and tested without breaking the transaction flow.

## Implementation details from the code

The Python implementation is not just a diagram; it is synthesizable hardware logic written in Amaranth.

### `Arbiter`

The arbiter is a synchronous state machine with one-hot grant bits:

- input signals: `req[0]`, `req[1]`, `ack`
- output: `gnt[0:1]`
- behavior:
  - if a transfer is acknowledged, the grant is cleared
  - if the current granted master still requests, it keeps the grant
  - otherwise, the highest-priority active request wins

### `AddressDecoder`

The decoder explicitly checks address boundaries:

- `0x0000 <= addr <= 0x0FFF` → slave 0
- `0x1000 <= addr <= 0x1FFF` → slave 1
- `0x2000 <= addr <= 0x27FF` → slave 2
- no match → `unmapped`

### `Slave`

Each slave is a RAM block implemented using Amaranth's `Memory` primitive:

- `read_port()` provides synchronous memory read
- `write_port()` handles writes when `sel & we` is active
- `ack` is a one-cycle pulse following selection
- `rdata` is valid together with the acknowledgement

### `SystemBus`

The top-level module combines all of the above:

- masters drive request and data signals
- a bus mux routes the granted master's address and data to the shared bus
- the decoder selects the active slave
- the selected slave performs the read/write
- the response path returns `rdata`, `ack`, and `err`
- `m_gnt` and `m_ack` are exposed per master

## Repository contents

- `amaranth_bus.py` — main HDL implementation and verification testbench
- `system_bus.v` — generated Verilog export from the Amaranth model
- `ARCHITECTURE.md` — architecture description
- `DIAGRAMS.md` — diagram references
- `README.md` — repository overview
- `out/` — generated VCD waveforms and exported HDL artifacts
- `*.svg` — timing and block diagrams
- `EN5102-AssignSysBus.pdf` — assignment reference material

## Simulation and verification

`amaranth_bus.py` contains a self-checking test suite that runs when the file is executed.

The script validates:

1. arbiter behavior
2. address decoder correctness
3. synchronous/asynchronous reset behavior
4. idle-state operation
5. single-master transactions
6. two-master arbitration
7. Verilog export

The testbench includes waveform generation to the `out/` directory.

## Running the project

### Prerequisites

Install Amaranth:

```bash
python3 -m pip install amaranth
```

### Run the design

From the repository root:

```bash
python3 amaranth_bus.py
```

This will:

- run the simulation tests
- generate VCD waveforms in `out/`
- export the design to `out/system_bus.v`

## Generated outputs

The `out/` directory contains simulation artifacts such as:

- `idle.vcd`
- `single_master.vcd`
- `two_masters.vcd`
- `system_bus.v`

## Notes

This project is intentionally simple and explicit so the bus protocol, arbitration logic, memory map, and verification flow are easy to follow. It demonstrates how a small shared-memory bus can be modeled and tested in a hardware-description language before exporting to Verilog for synthesis or FPGA workflows.

## Quick summary

This repository implements a compact Amaranth-based system bus with two masters, three memory-mapped slaves, fixed-priority arbitration, a 14-bit address decoder, and read/write acknowledgement/error handling suitable for digital design learning and HDL verification.
