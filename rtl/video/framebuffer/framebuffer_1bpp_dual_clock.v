// =============================================================================
// framebuffer_1bpp_dual_clock.v
// Packed 1bpp dual-clock framebuffer.
//
// CPU side writes and read-modify-write reads 32-bit packed words.
// Video side reads 32-bit packed words from the pixel clock domain.
// =============================================================================

module framebuffer_1bpp_dual_clock (
    input wire cpu_clk,
    input wire cpu_we,
    input wire [10:0] cpu_addr,
    input wire [31:0] cpu_wdata,
    output reg [31:0] cpu_rdata,

    input wire video_clk,
    input wire [10:0] video_addr,
    output reg [31:0] video_rdata
);
    reg [31:0] mem [0:2047] /* synthesis syn_ramstyle = "block_ram" */;

    always @(posedge cpu_clk) begin
        if (cpu_we) begin
            mem[cpu_addr] <= cpu_wdata;
            cpu_rdata <= cpu_wdata;
        end else begin
            cpu_rdata <= mem[cpu_addr];
        end
    end

    always @(posedge video_clk) begin
        video_rdata <= mem[video_addr];
    end
endmodule
