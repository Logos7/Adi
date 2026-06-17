module lcd_demo_rings(
    input [6:0] x,
    input [7:0] y,
    input [15:0] frame,
    output [15:0] rgb565
);

wire [6:0] cx = 7'd40 + {2'b00, frame[6:2]} - 7'd16;
wire [7:0] cy = 8'd80 + {1'b0, frame[7:2]} - 8'd32;
wire [7:0] dx = x > cx ? {1'b0, x - cx} : {1'b0, cx - x};
wire [7:0] dy = y > cy ? y - cy : cy - y;
wire [8:0] d = {1'b0, dx} + {1'b0, dy};
wire [4:0] v = d[5:1] + frame[5:1];
wire [4:0] r = v ^ {x[4:0]};
wire [5:0] g = {v, 1'b0} ^ y[5:0];
wire [4:0] b = ~v;

assign rgb565 = {r, g, b};

endmodule
