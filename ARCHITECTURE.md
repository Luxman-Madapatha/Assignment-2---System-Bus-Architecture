# System Bus Architecture

This repository implements a shared memory bus with two masters and three slave memory regions.

```mermaid
flowchart LR
    subgraph Masters["Masters"]
        M0["Master 0\nreq, we, addr, wdata"]
        M1["Master 1\nreq, we, addr, wdata"]
    end

    Arb["Arbiter\nFixed priority: M0 > M1\nGrant signal"]
    BusMux["Bus Mux\nSelects the granted master"]
    Dec["Address Decoder\n14-bit address -> slave select"]

    subgraph Slaves["Slave Memory Blocks"]
        S0["Slave 0\n0x0000 - 0x0FFF\n4 KB"]
        S1["Slave 1\n0x1000 - 0x1FFF\n4 KB"]
        S2["Slave 2\n0x2000 - 0x27FF\n2 KB"]
        Err["Unmapped address\nerr = 1, ack = 1"]
    end

    Res["Response Path\nrdata + ack"]

    M0 -->|request| Arb
    M1 -->|request| Arb

    Arb -->|grant (gnt)| BusMux
    BusMux -->|selected addr / data / we| Dec

    Dec -->|sel[0]| S0
    Dec -->|sel[1]| S1
    Dec -->|sel[2]| S2
    Dec -->|unmapped| Err

    S0 -->|ack / rdata| Res
    S1 -->|ack / rdata| Res
    S2 -->|ack / rdata| Res
    Err -->|ack / err| Res

    Res -->|ack / rdata| M0
    Res -->|ack / rdata| M1
```

## Bus behavior

- The arbiter grants access to only one master at a time.
- The granted master drives the shared bus.
- The address decoder chooses the correct slave using the address range.
- Each slave performs the read/write operation and returns acknowledgement plus data.
- Addresses outside the valid ranges are treated as unmapped and flagged with an error.

## Address map

- `0x0000 - 0x0FFF` -> Slave 0
- `0x1000 - 0x1FFF` -> Slave 1
- `0x2000 - 0x27FF` -> Slave 2
- Anything else -> unmapped

This diagram matches the design implemented in `amaranth_bus.py` and exported to `system_bus.v`.
