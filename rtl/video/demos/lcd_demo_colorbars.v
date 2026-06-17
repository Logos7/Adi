module lcd_demo_colorbars(
    input [6:0] x,
    input [7:0] y,
    input [15:0] frame,
    output reg [15:0] rgb565
);

wire [3:0] band = x[6:3] + frame[5:2];

always @* begin
    case (band[2:0])
        3'd0: rgb565 = 16'hF800;
        3'd1: rgb565 = 16'hFD20;
        3'd2: rgb565 = 16'hFFE0;
        3'd3: rgb565 = 16'h07E0;
        3'd4: rgb565 = 16'h07FF;
        3'd5: rgb565 = 16'h001F;
        3'd6: rgb565 = 16'hF81F;
        default: rgb565 = 16'hFFFF;
    endcase

    if (y[3:0] == frame[3:0]) begin
        rgb565 = 16'h0000;
    end
end

endmodule
