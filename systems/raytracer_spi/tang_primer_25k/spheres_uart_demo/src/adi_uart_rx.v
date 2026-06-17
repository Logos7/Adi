module adi_uart_rx #(
    parameter CLK_HZ = 27000000,
    parameter BAUD = 115200
)(
    input wire clk,
    input wire rst,
    input wire rx,
    output reg [7:0] data,
    output reg valid
);
    localparam integer DIV = CLK_HZ / BAUD;
    localparam integer HALF_DIV = DIV / 2;

    reg [3:0] state;
    reg [15:0] div_ctr;
    reg [2:0] bit_ctr;
    reg [7:0] shift;
    reg rx0;
    reg rx1;

    always @(posedge clk) begin
        if (rst) begin
            state <= 0;
            div_ctr <= 0;
            bit_ctr <= 0;
            shift <= 0;
            data <= 0;
            valid <= 0;
            rx0 <= 1;
            rx1 <= 1;
        end else begin
            rx0 <= rx;
            rx1 <= rx0;
            valid <= 0;

            case (state)
                0: begin
                    if (!rx1) begin
                        div_ctr <= HALF_DIV;
                        state <= 1;
                    end
                end
                1: begin
                    if (div_ctr == 0) begin
                        if (!rx1) begin
                            div_ctr <= DIV - 1;
                            bit_ctr <= 0;
                            state <= 2;
                        end else begin
                            state <= 0;
                        end
                    end else begin
                        div_ctr <= div_ctr - 1;
                    end
                end
                2: begin
                    if (div_ctr == 0) begin
                        shift <= {rx1, shift[7:1]};
                        div_ctr <= DIV - 1;
                        if (bit_ctr == 7) begin
                            state <= 3;
                        end else begin
                            bit_ctr <= bit_ctr + 1;
                        end
                    end else begin
                        div_ctr <= div_ctr - 1;
                    end
                end
                3: begin
                    if (div_ctr == 0) begin
                        data <= shift;
                        valid <= 1;
                        state <= 0;
                    end else begin
                        div_ctr <= div_ctr - 1;
                    end
                end
                default: state <= 0;
            endcase
        end
    end
endmodule
