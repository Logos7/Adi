// =============================================================================
// uart_tx.v
// Minimalny nadajnik UART 8N1, Verilog-2001 / Gowin-safe.
// Domyślnie: clk 27 MHz, baud ~115200 przez CLKS_PER_BIT=234.
// =============================================================================

module uart_tx #(
    parameter CLKS_PER_BIT = 234
)(
    input  wire       clk,
    input  wire       rst,
    input  wire [7:0] data,
    input  wire       valid,
    output wire       ready,
    output reg        tx
);

    reg        busy;
    reg [15:0] clk_count;
    reg [3:0]  bit_index;
    reg [9:0]  shifter;

    assign ready = ~busy;

    always @(posedge clk) begin
        if (rst) begin
            busy      <= 1'b0;
            clk_count <= 16'd0;
            bit_index <= 4'd0;
            shifter   <= 10'b11_1111_1111;
            tx        <= 1'b1;
        end else begin
            if (!busy) begin
                tx <= 1'b1;
                if (valid) begin
                    // Format 8N1: start=0, data LSB first, stop=1.
                    busy      <= 1'b1;
                    clk_count <= 16'd0;
                    bit_index <= 4'd0;
                    shifter   <= {1'b1, data, 1'b0};
                    tx        <= 1'b0;
                end
            end else begin
                if (clk_count == (CLKS_PER_BIT - 1)) begin
                    clk_count <= 16'd0;
                    if (bit_index == 4'd9) begin
                        busy      <= 1'b0;
                        bit_index <= 4'd0;
                        shifter   <= 10'b11_1111_1111;
                        tx        <= 1'b1;
                    end else begin
                        bit_index <= bit_index + 4'd1;
                        shifter   <= {1'b1, shifter[9:1]};
                        tx        <= shifter[1];
                    end
                end else begin
                    clk_count <= clk_count + 16'd1;
                end
            end
        end
    end

endmodule
