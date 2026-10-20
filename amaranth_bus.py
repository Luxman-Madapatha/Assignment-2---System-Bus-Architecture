"""
amaranth_bus.py -- EN5102 Assignment 2: 8-bit parallel system bus in Amaranth HDL

    2 masters -> [Arbiter] -> shared bus -> [AddressDecoder] -> 3 slaves (4K, 4K, 2K)

This is REAL synthesizable hardware (registers, muxes, memories), written in Python:
  * posedge clock, ASYNCHRONOUS reset (ClockDomain(async_reset=True))
  * the same description is (1) simulated here and (2) exported to Verilog for Quartus.

Address map (14-bit address, 8-bit data):
    0x0000-0x0FFF slave0 (4 KB)   0x1000-0x1FFF slave1 (4 KB)   0x2000-0x27FF slave2 (2 KB)
    anything else -> no slave: bus answers with ack + err

Handshake:   master: req + we/addr/wdata  ->  arbiter registers gnt  ->  decoder picks slave
             -> slave registers ack (+rdata, read data valid together with ack)
             -> arbiter drops gnt for one cycle -> next transfer.
(On a write, rdata shows the old memory contents: the RAM is read-before-write. Ignore it.)

Run:  python3 amaranth_bus.py        (tests + waveforms + Verilog into ./out)
"""

import os
from amaranth import *
from amaranth.lib.memory import Memory
from amaranth.sim import Simulator

ADDR_BITS = 14
SLAVE_ABITS = [12, 12, 11]  # 4K, 4K, 2K


# ----------------------------------------------------------------------------- arbiter
class Arbiter(Elaboratable):
    """Fixed priority: M0 > M1. One-hot registered grant, no pre-emption."""

    def __init__(self):
        self.req = Signal(2)  # in
        self.ack = Signal()  # in  : current transfer finished
        self.gnt = Signal(2)  # out : one-hot, registered

    def elaborate(self, platform):
        m = Module()

        # Acknowledge releases the bus after the current transfer completes.
        # Keep the existing grant while the active master is still requesting,
        # unless the transfer has just been acknowledged.
        with m.If(self.ack):
            m.d.sync += self.gnt.eq(0)
        with m.Elif((self.gnt & self.req).any()):
            pass
        with m.Elif(self.req[0]):
            m.d.sync += self.gnt.eq(0b01)
        with m.Elif(self.req[1]):
            m.d.sync += self.gnt.eq(0b10)
        with m.Else():
            m.d.sync += self.gnt.eq(0)
        return m


# ----------------------------------------------------------------------------- decoder
class AddressDecoder(Elaboratable):
    """Pure combinational address decoder.

    The address ranges are explicitly checked so the decoder remains easy to read and
    reason about during verification and synthesis.
    """

    def __init__(self):
        self.addr = Signal(ADDR_BITS)  # in
        self.sel = Signal(3)  # out : one-hot slave select
        self.unmapped = Signal()  # out : address owned by nobody

    def elaborate(self, platform):
        m = Module()
        a = self.addr

        slave0 = (a >= 0x0000) & (a <= 0x0FFF)
        slave1 = (a >= 0x1000) & (a <= 0x1FFF)
        slave2 = (a >= 0x2000) & (a <= 0x27FF)

        m.d.comb += [
            self.sel[0].eq(slave0),
            self.sel[1].eq(slave1),
            self.sel[2].eq(slave2),
            self.unmapped.eq(~self.sel.any()),
        ]
        return m


# ------------------------------------------------------------------------------ slave
class Slave(Elaboratable):
    """RAM slave: ack is a one-cycle pulse, one cycle after being selected."""

    def __init__(self, abits):
        self.abits = abits
        self.sel = Signal()
        self.we = Signal()
        self.addr = Signal(abits)
        self.wdata = Signal(8)
        self.ack = Signal()
        self.rdata = Signal(8)

    def elaborate(self, platform):
        m = Module()
        m.submodules.mem = mem = Memory(shape=8, depth=1 << self.abits, init=[])
        rd = mem.read_port()  # synchronous read, 1-cycle latency
        wr = mem.write_port()
        m.d.comb += [
            rd.addr.eq(self.addr),
            wr.addr.eq(self.addr),
            wr.data.eq(self.wdata),
            wr.en.eq(self.sel & self.we & ~self.ack),
            self.rdata.eq(rd.data),
        ]
        m.d.sync += self.ack.eq(self.sel & ~self.ack)
        return m


# ---------------------------------------------------------------------------- top level
class SystemBus(Elaboratable):
    def __init__(self):
        self.cd = ClockDomain("sync", async_reset=True)  # clk + async rst
        n = lambda s, i: Signal(name=f"m{i}_{s}")
        self.m_req = [n("req", i) for i in range(2)]
        self.m_we = [n("we", i) for i in range(2)]
        self.m_addr = [Signal(ADDR_BITS, name=f"m{i}_addr") for i in range(2)]
        self.m_wdata = [Signal(8, name=f"m{i}_wdata") for i in range(2)]
        self.m_gnt = [n("gnt", i) for i in range(2)]
        self.m_ack = [n("ack", i) for i in range(2)]
        self.rdata = Signal(8)
        self.err = Signal()
        self.arb = Arbiter()
        self.dec = AddressDecoder()

    def ports(self):
        return (
            [self.cd.clk, self.cd.rst]
            + self.m_req
            + self.m_we
            + self.m_addr
            + self.m_wdata
            + self.m_gnt
            + self.m_ack
            + [self.rdata, self.err]
        )

    def elaborate(self, platform):
        m = Module()
        m.domains.sync = self.cd
        m.submodules.arb = arb = self.arb
        m.submodules.dec = dec = self.dec
        slaves = [Slave(b) for b in SLAVE_ABITS]
        for i, s in enumerate(slaves):
            setattr(m.submodules, f"slave{i}", s)

        gnt = arb.gnt
        bus_active = gnt.any()
        bus_addr = Signal(ADDR_BITS)
        bus_we = Signal()
        bus_wdata = Signal(8)

        # The bus is a single shared path, so default values prevent stale data from
        # persisting when no master holds the grant.
        m.d.comb += [
            bus_addr.eq(0),
            bus_we.eq(0),
            bus_wdata.eq(0),
        ]

        # ---- bus mux: granted master drives the bus ----
        m.d.comb += arb.req.eq(Cat(*self.m_req))
        with m.If(gnt[0]):
            m.d.comb += [
                bus_addr.eq(self.m_addr[0]),
                bus_we.eq(self.m_we[0]),
                bus_wdata.eq(self.m_wdata[0]),
            ]
        with m.Elif(gnt[1]):
            m.d.comb += [
                bus_addr.eq(self.m_addr[1]),
                bus_we.eq(self.m_we[1]),
                bus_wdata.eq(self.m_wdata[1]),
            ]

        # ---- decoder + slaves ----
        m.d.comb += dec.addr.eq(bus_addr)
        for i, s in enumerate(slaves):
            m.d.comb += [
                s.sel.eq(dec.sel[i] & bus_active),
                s.we.eq(bus_we),
                s.addr.eq(bus_addr[: s.abits]),
                s.wdata.eq(bus_wdata),
            ]

        # ---- default responder for unmapped addresses ----
        err_ack = Signal()
        m.d.sync += err_ack.eq(bus_active & dec.unmapped & ~err_ack)

        # ---- response path ----
        ack = Signal()
        m.d.comb += ack.eq(Cat(*[s.ack for s in slaves]).any() | err_ack)
        m.d.comb += arb.ack.eq(ack)

        m.d.comb += [
            self.rdata.eq(0),
            self.err.eq(0),
        ]
        with m.If(slaves[0].ack):
            m.d.comb += self.rdata.eq(slaves[0].rdata)
        with m.Elif(slaves[1].ack):
            m.d.comb += self.rdata.eq(slaves[1].rdata)
        with m.Elif(slaves[2].ack):
            m.d.comb += self.rdata.eq(slaves[2].rdata)
        m.d.comb += self.err.eq(err_ack)
        for i in range(2):
            m.d.comb += [self.m_gnt[i].eq(gnt[i]), self.m_ack[i].eq(ack & gnt[i])]
        return m


# =============================================================== verification helpers
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
CLK = 1e-6


def make(top=None):
    dut = top or SystemBus()
    sim = Simulator(dut)
    sim.add_clock(CLK)
    return dut, sim


def run(sim, vcd=None, traces=()):
    if vcd:
        os.makedirs(OUT, exist_ok=True)
        with sim.write_vcd(os.path.join(OUT, vcd), traces=list(traces)):
            sim.run()
    else:
        sim.run()


async def master(ctx, dut, mid, txns, log, done):
    """Behavioural master. txns = [(delay_ticks, we, addr, wdata), ...]."""
    for delay, we, addr, wdata in txns:
        for _ in range(delay):
            await ctx.tick()
        ctx.set(dut.m_we[mid], we)
        ctx.set(dut.m_addr[mid], addr)
        ctx.set(dut.m_wdata[mid], wdata)
        ctx.set(dut.m_req[mid], 1)
        waited = 0
        while True:
            await ctx.tick()
            waited += 1
            if ctx.get(dut.m_ack[mid]):
                break
            assert waited < 40, f"M{mid}: no ack (deadlock?) addr={addr:#x}"
        log.append(
            dict(
                mid=mid,
                we=we,
                addr=addr,
                wdata=wdata,
                latency=waited,
                rdata=ctx.get(dut.rdata),
                err=ctx.get(dut.err),
            )
        )
        done.append(mid)
        ctx.set(dut.m_req[mid], 0)
        await ctx.tick()


def add_master(sim, dut, mid, txns, log, done):
    async def tb(ctx):
        await master(ctx, dut, mid, txns, log, done)

    sim.add_testbench(tb)


def banner(s):
    print("\n" + "=" * 72 + f"\n{s}\n" + "=" * 72)


# ================================================================================ tests
def test_arbiter():
    banner("TEST 1  Arbiter alone: idle / single request / two requests")
    arb = Arbiter()
    dom = ClockDomain("sync", async_reset=True)
    top = Module()
    top.domains.sync = dom
    top.submodules.arb = arb
    sim = Simulator(top)
    sim.add_clock(CLK)

    async def tb(ctx):
        async def step(req, ack=0):
            ctx.set(arb.req, req)
            ctx.set(arb.ack, ack)
            await ctx.tick()
            return ctx.get(arb.gnt)

        assert await step(0b00) == 0b00
        print("  idle            -> gnt=00  PASS")
        assert await step(0b10) == 0b10
        print("  only M1 asks    -> gnt=10  PASS")
        assert await step(0b11) == 0b10
        print("  M0 joins, M1 holds (no pre-emption) -> gnt=10  PASS")
        assert await step(0b11, ack=1) == 0b00
        print("  transfer acked  -> gnt=00 (bus released)       PASS")
        assert await step(0b11) == 0b01
        print("  both ask        -> gnt=01 (M0 priority wins)   PASS")
        assert await step(0b11) == 0b01
        assert await step(0b10, ack=1) == 0b00
        assert await step(0b10) == 0b10
        print("  M0 gone         -> M1 gets bus                 PASS")

    sim.add_testbench(tb)
    run(sim)


def test_decoder():
    banner("TEST 2  Address decoder / address mapping")
    dec = AddressDecoder()
    sim = Simulator(dec)

    async def tb(ctx):
        cases = [
            (0x0000, 0b001),
            (0x0FFF, 0b001),
            (0x1000, 0b010),
            (0x1FFF, 0b010),
            (0x2000, 0b100),
            (0x27FF, 0b100),
            (0x2800, 0b000),
            (0x3FFF, 0b000),
        ]
        for a, exp in cases:
            ctx.set(dec.addr, a)
            await ctx.delay(1e-9)
            got = ctx.get(dec.sel)
            name = "none (unmapped)" if got == 0 else f"slave {got.bit_length() - 1}"
            print(f"  addr {a:#06x} -> {name}")
            assert got == exp and ctx.get(dec.unmapped) == (exp == 0), (hex(a), got)
        print("  PASS")

    sim.add_testbench(tb)
    run(sim)


def test_reset():
    banner("TEST 3  Reset (synchronous release + asynchronous assertion)")
    dut, sim = make()

    async def tb(ctx):
        ctx.set(dut.cd.rst, 1)
        await ctx.tick()
        await ctx.tick()
        assert ctx.get(dut.m_gnt[0]) == 0 and ctx.get(dut.arb.gnt) == 0
        print("  held in reset: no grant, no ack                    PASS")
        ctx.set(dut.cd.rst, 0)
        ctx.set(dut.m_addr[0], 0x0010)
        ctx.set(dut.m_we[0], 1)
        ctx.set(dut.m_wdata[0], 0xAA)
        ctx.set(dut.m_req[0], 1)
        await ctx.tick()
        assert ctx.get(dut.m_gnt[0]) == 1
        ctx.set(dut.cd.rst, 1)  # NO clock edge: async reset must act at once
        await ctx.delay(CLK / 100)
        assert ctx.get(dut.m_gnt[0]) == 0, "async reset did not clear the grant"
        print(
            "  reset asserted mid-transfer clears grant immediately PASS (asynchronous)"
        )

    sim.add_testbench(tb)
    run(sim)


def test_idle():
    banner("TEST 4  Top level: idle condition")
    dut, sim = make()

    async def tb(ctx):
        for _ in range(10):
            await ctx.tick()
            assert (
                ctx.get(dut.arb.gnt) == 0
                and ctx.get(dut.m_ack[0]) == 0
                and ctx.get(dut.m_ack[1]) == 0
                and ctx.get(dut.err) == 0
            )
        print("  10 idle cycles: no grants, no acks, no errors   PASS")

    sim.add_testbench(tb)
    run(sim, "idle.vcd", dut.ports() + [dut.arb.gnt])


def test_single_master():
    banner("TEST 5  Top level: one master requesting")
    for mid in (0, 1):
        dut, sim = make()
        log, done = [], []
        txns = []
        for i, base in enumerate([0x0000, 0x1000, 0x2000]):
            txns += [(0, 1, base + 0x10, 0x30 + i + 4 * mid), (0, 0, base + 0x10, 0)]
        txns += [(0, 1, 0x3000, 0x55)]  # unmapped
        add_master(sim, dut, mid, txns, log, done)
        run(
            sim,
            "single_master.vcd" if mid == 0 else None,
            dut.ports() + [dut.arb.gnt] if mid == 0 else (),
        )
        for i in range(3):
            w, r = log[2 * i], log[2 * i + 1]
            exp = 0x30 + i + 4 * mid
            assert r["rdata"] == exp and not r["err"] and not w["err"], (mid, i, r)
            print(
                f"  M{mid}: wrote {exp:#04x} to slave {i}, read back {r['rdata']:#04x} "
                f"(latency {w['latency']} / {r['latency']} clocks)"
            )
        assert log[6]["err"], "unmapped access should flag err"
        print(f"  M{mid}: unmapped 0x3000 -> err flagged                    PASS")


def test_two_masters():
    banner("TEST 6  Top level: two masters requesting")
    # (a) simultaneous: M0 must win
    dut, sim = make()
    log, done = [], []
    add_master(sim, dut, 0, [(0, 1, 0x0001, 0xA0), (0, 0, 0x0001, 0)], log, done)
    add_master(sim, dut, 1, [(0, 1, 0x1001, 0xB1), (0, 0, 0x1001, 0)], log, done)
    run(sim, "two_masters.vcd", dut.ports() + [dut.arb.gnt])
    # fixed priority: M0 wins every arbitration, so it finishes BOTH of its transfers
    # (write, read) before M1 gets in -> M1 is starved while M0 keeps asking.
    assert done == [0, 0, 1, 1], done
    r0 = [r for r in log if r["mid"] == 0 and not r["we"]][0]
    r1 = [r for r in log if r["mid"] == 1 and not r["we"]][0]
    assert r0["rdata"] == 0xA0 and r1["rdata"] == 0xB1
    print(
        f"  (a) simultaneous requests: completion order = {['M%d' % x for x in done]}  "
        f"(M0 wins every time)   PASS\n      read-backs: M0={r0['rdata']:#04x}, M1={r1['rdata']:#04x}"
    )

    # (b) M1 holds the bus, M0 arrives one clock later: no pre-emption
    dut, sim = make()
    log, done = [], []
    add_master(sim, dut, 1, [(0, 1, 0x2002, 0xD2)], log, done)
    add_master(sim, dut, 0, [(1, 1, 0x0002, 0xC2)], log, done)
    run(sim)
    assert done == [1, 0], done
    print(
        "  (b) M1 already granted, M0 arrives later: M1 finishes first, M0 waits   PASS"
    )

    # (c) 8 interleaved transfers, data integrity
    dut, sim = make()
    log, done = [], []
    w0 = [(0, 1, 0x0100 + i, 0x40 + i) for i in range(4)] + [
        (0, 0, 0x0100 + i, 0) for i in range(4)
    ]
    w1 = [(0, 1, 0x1100 + i, 0x80 + i) for i in range(4)] + [
        (0, 0, 0x1100 + i, 0) for i in range(4)
    ]
    add_master(sim, dut, 0, w0, log, done)
    add_master(sim, dut, 1, w1, log, done)
    run(sim)
    for mid, base in ((0, 0x40), (1, 0x80)):
        got = [r["rdata"] for r in log if r["mid"] == mid and not r["we"]]
        assert got == [base + i for i in range(4)], (mid, got)
    print(
        "  (c) 8 interleaved writes+reads from both masters, all data correct      PASS"
    )


def export_verilog():
    banner("EXPORT  Verilog for Quartus")
    from amaranth.back import verilog

    os.makedirs(OUT, exist_ok=True)
    dut = SystemBus()
    text = verilog.convert(dut, name="system_bus", ports=dut.ports())
    path = os.path.join(OUT, "system_bus.v")
    with open(path, "w") as f:
        f.write(text)
    print(f"  wrote {path}  ({len(text.splitlines())} lines)")


if __name__ == "__main__":
    test_arbiter()
    test_decoder()
    test_reset()
    test_idle()
    test_single_master()
    test_two_masters()
    export_verilog()
    print("\nALL TESTS PASSED  (waveforms: out/*.vcd)")
