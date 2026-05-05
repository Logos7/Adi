// =============================================================================
// uart_rx.v
// Prosty odbiornik UART 8N1 dla Brahma-Bija bootloadera.
// Verilog-2001 / Gowin-safe.
// =============================================================================

module uart_rx #(
    parameter CLKS_PER_BIT = 234
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       rx,
    output reg  [7:0] data,
    output reg        valid
);

    localparam [2:0] S_IDLE  = 3'd0;
    localparam [2:0] S_START = 3'd1;
    localparam [2:0] S_DATA  = 3'd2;
    localparam [2:0] S_STOP  = 3'd3;

    reg [2:0]  state;
    reg [15:0] clk_count;
    reg [2:0]  bit_index;
    reg [7:0]  data_work;
    reg        rx_meta;
    reg        rx_sync;

    always @(posedge clk) begin
        if (rst) begin
            state      <= S_IDLE;
            clk_count  <= 16'd0;
            bit_index  <= 3'd0;
            data_work  <= 8'd0;
            rx_meta    <= 1'b1;
            rx_sync    <= 1'b1;
            data       <= 8'd0;
            valid      <= 1'b0;
        end else begin
            rx_meta <= rx;
            rx_sync <= rx_meta;
            valid <= 1'b0;

            case (state)
                S_IDLE: begin
                    clk_count <= 16'd0;
                    bit_index <= 3'd0;
                    if (rx_sync == 1'b0) begin
                        state <= S_START;
                    end
                end

                S_START: begin
                    if (clk_count == (CLKS_PER_BIT / 2)) begin
                        if (rx_sync == 1'b0) begin
                            clk_count <= 16'd0;
                            state     <= S_DATA;
                        end else begin
                            state <= S_IDLE;
                        end
                    end else begin
                        clk_count <= clk_count + 16'd1;
                    end
                end

                S_DATA: begin
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        clk_count <= 16'd0;
                        data_work[bit_index] <= rx_sync;
                        if (bit_index == 3'd7) begin
                            bit_index <= 3'd0;
                            state     <= S_STOP;
                        end else begin
                            bit_index <= bit_index + 3'd1;
                        end
                    end else begin
                        clk_count <= clk_count + 16'd1;
                    end
                end

                S_STOP: begin
                    if (clk_count == CLKS_PER_BIT - 1) begin
                        clk_count <= 16'd0;
                        data      <= data_work;
                        valid     <= 1'b1;
                        state     <= S_IDLE;
                    end else begin
                        clk_count <= clk_count + 16'd1;
                    end
                end

                default: begin
                    state <= S_IDLE;
                end
            endcase
        end
    end

endmodule
