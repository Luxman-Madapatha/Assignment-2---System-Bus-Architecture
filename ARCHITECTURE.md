# System Bus Architecture

This repository implements a shared memory bus with two masters and three slave memory regions.

```text
+-------------------+       +---------------------+       +---------------------+
| Master 0          |       | Master 1            |       |                     |
| req, we, addr,    |       | req, we, addr,      |       |                     |
| wdata             |       | wdata               |       |                     |
+---------+---------+       +----------+----------+       |                     |
          |                              |                          |
          |                              |                          |
          v                              v                          v
   +-------------------+      +-------------------+      +-------------------+
   | Arbiter           |----->| Bus Mux           |----->| Address Decoder  |
   | Fixed priority    |      | Selects granted   |      | 14-bit address    |
   | M0 > M1           |      | master            |      | -> slave select   |
   +-------------------+      +-------------------+      +---------+---------+
                                                                        |
                        +-------------------------------------------+-------------------------------------------+
                        |                                                                                 |
                        v                                                                                 v
           +-----------------------+                          +-----------------------+      +---------------------------+
           | Slave 0               |                          | Slave 1               |      | Slave 2                   |
           | 0x0000 - 0x0FFF       |                          | 0x1000 - 0x1FFF      |      | 0x2000 - 0x27FF          |
           | 4 KB                  |                          | 4 KB                  |      | 2 KB                     |
           +-----------+-----------+                          +-----------+-----------+      +------------+------------+
                       |                                                      |                               |
                       |                                                      |                               |
                       +-----------------------------+----------------------------+-------------------------------+
                                                         |
                                                         v
                                            +---------------------------+
                                            | Response Path            |
                                            | rdata + ack + err        |
                                            +---------------------------+
                                                         |
                                                         |
                                                         +---------------------------+
                                                                     |
                                                                     v
                                                       +-------------------+
                                                       | Masters receive  |
                                                       | ack / rdata      |
                                                       +-------------------+


Unmapped address behavior:
- If address is outside the valid ranges, the decoder selects no slave.
- The system raises err = 1 and ack = 1.
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
