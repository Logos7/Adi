module adi_spi_byte_tx #(
    parameter CLK_DIV = 2
)(
    input wire clk,
    input wire rst,
    input wire start,
    input wire [7:0] data,
    output reg busy,
    output reg done,
    output reg sck,
    output reg mosi
);
    reg [7:0] shift;
    reg [3:0] bit_ctr;
    reg [15:0] div_ctr;
    reg phase;

    always @(posedge clk) begin
        if (rst) begin
            shift <= 0;
            bit_ctr <= 0;
            div_ctr <= 0;
            phase <= 0;
            busy <= 0;
            done <= 0;
            sck <= 0;
            mosi <= 0;
        end else begin
            done <= 0;

            if (!busy) begin
                sck <= 0;
                if (start) begin
                    shift <= data;
                    bit_ctr <= 7;
                    div_ctr <= CLK_DIV - 1;
                    phase <= 0;
                    busy <= 1;
                    mosi <= data[7];
                end
            end else begin
                if (div_ctr != 0) begin
                    div_ctr <= div_ctr - 1;
                end else begin
                    div_ctr <= CLK_DIV - 1;
                    if (!phase) begin
                        sck <= 1;
                        phase <= 1;
                    end else begin
                        sck <= 0;
                        phase <= 0;
                        if (bit_ctr == 0) begin
                            busy <= 0;
                            done <= 1;
                        end else begin
                            bit_ctr <= bit_ctr - 1;
                            shift <= {shift[6:0], 1'b0};
                            mosi <= shift[6];
                        end
                    end
                end
            end
        end
    end
endmodule
