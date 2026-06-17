module lcd_demo_plasma(
    input [6:0] x,
    input [7:0] y,
    input [15:0] frame,
    output [15:0] rgb565
);

wire [7:0] a = {1'b0, x} + y + frame[7:0];
wire [7:0] b = {1'b0, x} - y + {frame[6:0], 1'b0};
wire [7:0] c = ({1'b0, x} ^ y) + {frame[5:0], 2'b00};
wire [4:0] r = a[7:3] ^ c[6:2];
wire [5:0] g = b[7:2] ^ a[6:1];
wire [4:0] bl = c[7:3] ^ b[6:2];

assign rgb565 = {r, g, bl};

endmodule
