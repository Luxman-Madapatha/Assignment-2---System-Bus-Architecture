# What this assignment asks you to build

This is a different assignment from the 8b/10b one we just did. It's **Assignment 2 of EN5102 Digital Systems Design: design an 8-bit parallel bus**.

## The big picture: a shared road with a traffic controller

Think of a small town with one single-lane road, which is the **bus**.

- **Masters** are the drivers. They start every conversation, for example "write this value to that location" or "read what's at that location". You have **2 masters**.
- **Slaves** are the destinations, such as memory blocks that store or return data when asked. You have **3 slaves**, with **4K, 4K and 2K** of memory (4096, 4096 and 2048 locations).
- **8-bit** means each transfer carries 8 bits (one byte) of data at a time.

Only one master can use the road at a time. If both want it, someone has to decide who goes first. If a master asks for a location, something has to work out which slave owns that address. Those two jobs are the core of the assignment.

## The two key pieces you design

**1. The arbiter** is the traffic controller. It uses **priority-based arbitration**. If both masters request the bus at once, the higher-priority master wins and the other waits.

**2. The address decoder** is the postal sorter. A master sends an address, and the decoder looks at it and decides which of the 3 slaves it belongs to. For example, addresses 0–4095 go to slave 1, the next 4096 to slave 2, and the last 2048 to slave 3. This is called the **address mapping**, and you get to define it.

## The tasks, in plain words

| # | Task | What it means |
|---|---|---|
| 1 | Arbiter design | Write the hardware description of the traffic controller |
| 2 | Arbiter verification | Prove it works in three situations: nobody asks, one master asks, both ask |
| 3 | Address decoder | Build the sorter and test that each address reaches the right slave, across all 3 |
| 4 | Top-level verification | Join everything into one system and test it: **a)** reset (does it start cleanly?), **b)** idle (nothing happens when nothing is requested), **c)** one master requesting, **d)** two masters requesting |

**Technical constraints:** you write the design in RTL (a hardware description language such as Verilog), using an **asynchronous reset** (reset works instantly, without waiting for the clock) and a **posedge clock** (things change on the clock's rising edge).

## The hardware part (the red bullet)

You need to run this on real hardware, not just in simulation. The board is the **Altera DE0**, an FPGA development board (the picture on page 3). An FPGA is a chip you can reconfigure into any digital circuit.

- **Board 1** holds your bus design (arbiter and decoder).
- **Board 2** pretends to be the masters and slaves, acting as the drivers and the destinations.

You'd wire the two boards together through the expansion headers, so a real bus runs between them.

## Using the board's controls (the guidelines slide)

1. **One push-button** is the reset.
2. **The 7-segment display** shows the current mode: **1** = idle, **2** = one master requesting, **3** = two masters requesting.
3. **4 switches** set the address (bits 3 to 0), and the higher address bits are fixed at 0.
4. **4 other switches** set the data (bits 3 to 0), and the higher data bits are fixed at 0.

In effect, you flip switches to choose an address and a value, and the display tells you what scenario you're in.

## Grading and deadline

- **Report: 20 marks.** It must include functional descriptions (what each block does), IO definitions (every input and output), timing diagrams, and the RTL and testbench code.
- **Live demo: 20 marks.**
- **Deadline:** 15 days from the day it was handed out.

## Two things in the slides worth checking

- The title says "Assignment 2" but the guidelines slide says "Assignment 3". This is probably a typo, but confirm with your lecturer.
- If the upper address bits are fixed at 0, the 4 address switches can only reach the lowest 16 addresses. That would all land in slave 1 under a simple mapping, so you may need to ask how to demonstrate slaves 2 and 3 on the board.

I can sketch the block diagram, propose an address map, or write the arbiter and decoder in Verilog with a testbench, as I did for the 8b/10b task.
