// =============================================================================
// framebuffer_1bpp_dual_clock.v
// 1bpp dual-clock framebuffer, one stored bit per pixel.
//
// Gowin note:
// This RAM intentionally has a write-only CPU port and a read-only video port.
// There is no read-before-write behavior on the write port, so Gowin should infer
// a supported DPB write mode instead of WRITE_MODE0 = 2'b10.
// =============================================================================

module framebuffer_1bpp_dual_clock #(
    parameter ADDR_BITS = 17,
    parameter PIXELS = 131072
) (
    input wire cpu_clk,
    input wire cpu_we,
    input wire [ADDR_BITS-1:0] cpu_addr,
    input wire cpu_wdata,
    input wire video_clk,
    input wire [ADDR_BITS-1:0] video_addr,
    output reg video_rdata
);
    reg mem [0:PIXELS-1] /* synthesis syn_ramstyle = "block_ram" */;

    always @(posedge cpu_clk) begin
        if (cpu_we)
            mem[cpu_addr] <= cpu_wdata;
    end

    always @(posedge video_clk) begin
        video_rdata <= mem[video_addr];
    end
endmodule
