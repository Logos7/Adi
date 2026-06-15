module spi_lcd_master #(
    parameter DIVIDER = 2
)(
    input clk,
    input rst,
    input start,
    input dc_in,
    input [7:0] data_in,
    output reg busy,
    output reg done,
    output reg sck,
    output reg cs,
    output reg dc,
    output reg mosi
);

reg [15:0] div_count = 16'd0;
reg [7:0] shifter = 8'd0;
reg [2:0] bit_index = 3'd0;
reg phase = 1'b0;

wire tick = div_count == (DIVIDER - 1);

always @(posedge clk) begin
    if (rst) begin
        busy <= 1'b0;
        done <= 1'b0;
        sck <= 1'b0;
        cs <= 1'b1;
        dc <= 1'b1;
        mosi <= 1'b1;
        div_count <= 16'd0;
        shifter <= 8'd0;
        bit_index <= 3'd7;
        phase <= 1'b0;
    end else begin
        done <= 1'b0;

        if (!busy) begin
            sck <= 1'b0;
            cs <= 1'b1;
            div_count <= 16'd0;
            phase <= 1'b0;
            if (start) begin
                busy <= 1'b1;
                cs <= 1'b0;
                dc <= dc_in;
                shifter <= data_in;
                bit_index <= 3'd7;
                mosi <= data_in[7];
            end
        end else begin
            if (tick) begin
                div_count <= 16'd0;
                if (!phase) begin
                    sck <= 1'b1;
                    phase <= 1'b1;
                end else begin
                    sck <= 1'b0;
                    phase <= 1'b0;
                    if (bit_index == 3'd0) begin
                        busy <= 1'b0;
                        cs <= 1'b1;
                        done <= 1'b1;
                    end else begin
                        bit_index <= bit_index - 3'd1;
                        shifter <= {shifter[6:0], 1'b0};
                        mosi <= shifter[6];
                    end
                end
            end else begin
                div_count <= div_count + 16'd1;
            end
        end
    end
end

endmodule
