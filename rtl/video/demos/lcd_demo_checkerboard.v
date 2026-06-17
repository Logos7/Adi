module lcd_demo_checkerboard(
    input [6:0] x,
    input [7:0] y,
    input [15:0] frame,
    output reg [15:0] rgb565
);

wire [6:0] xx = x + frame[5:0];
wire [7:0] yy = y + {2'd0, frame[5:0]};
wire tile = xx[3] ^ yy[3];
wire fine = xx[1] ^ yy[1];

always @* begin
    if (tile) begin
        rgb565 = fine ? 16'h07E0 : 16'h0520;
    end else begin
        rgb565 = fine ? 16'hFFFF : 16'hBDF7;
    end
end

endmodule
