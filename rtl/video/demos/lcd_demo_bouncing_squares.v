module lcd_demo_bouncing_squares(
    input [6:0] x,
    input [7:0] y,
    input [15:0] frame,
    output reg [15:0] rgb565
);

wire [7:0] t = frame[7:0];
wire [6:0] sx0 = t[6] ? 7'd63 - t[5:0] : t[5:0];
wire [7:0] sy0 = t[7] ? 8'd127 - {1'b0, t[6:0]} : {1'b0, t[6:0]};
wire [6:0] sx1 = t[6] ? t[5:0] : 7'd63 - t[5:0];
wire [7:0] sy1 = t[7] ? {1'b0, t[6:0]} : 8'd127 - {1'b0, t[6:0]};
wire [6:0] sx2 = 7'd10 + {1'b0, t[5:1]};
wire [7:0] sy2 = 8'd20 + {1'b0, t[6:1]};
wire [6:0] sx3 = 7'd5 + {2'b00, t[4:0]};
wire [7:0] sy3 = 8'd100 + {3'b000, t[4:0]};
wire [6:0] sx4 = 7'd38 + {2'b00, t[4:0]};
wire [7:0] sy4 = 8'd45 + {2'b00, t[5:0]};
wire [6:0] sx5 = 7'd20 + {3'b000, t[3:0]};
wire [7:0] sy5 = 8'd70 + {1'b0, t[6:0]};

always @* begin
    rgb565 = 16'h0000;
    if (inside(x, y, sx0, sy0, 5'd12)) rgb565 = border(x, y, sx0, sy0, 5'd12, 16'hF800);
    else if (inside(x, y, sx1, sy1, 5'd10)) rgb565 = border(x, y, sx1, sy1, 5'd10, 16'h07E0);
    else if (inside(x, y, sx2, sy2, 5'd14)) rgb565 = border(x, y, sx2, sy2, 5'd14, 16'h001F);
    else if (inside(x, y, sx3, sy3, 5'd9)) rgb565 = border(x, y, sx3, sy3, 5'd9, 16'hFFE0);
    else if (inside(x, y, sx4, sy4, 5'd11)) rgb565 = border(x, y, sx4, sy4, 5'd11, 16'hF81F);
    else if (inside(x, y, sx5, sy5, 5'd8)) rgb565 = border(x, y, sx5, sy5, 5'd8, 16'h07FF);
end

function inside;
    input [6:0] px;
    input [7:0] py;
    input [6:0] sx;
    input [7:0] sy;
    input [4:0] size;
    reg [7:0] right;
    reg [7:0] bottom;
    begin
        right = {1'b0, sx} + {3'b000, size} - 8'd1;
        bottom = sy + {3'b000, size} - 8'd1;
        inside = ({1'b0, px} >= {1'b0, sx}) && ({1'b0, px} <= right) && (py >= sy) && (py <= bottom);
    end
endfunction

function [15:0] border;
    input [6:0] px;
    input [7:0] py;
    input [6:0] sx;
    input [7:0] sy;
    input [4:0] size;
    input [15:0] fill;
    reg [7:0] right;
    reg [7:0] bottom;
    begin
        right = {1'b0, sx} + {3'b000, size} - 8'd1;
        bottom = sy + {3'b000, size} - 8'd1;
        if ({1'b0, px} == {1'b0, sx} || {1'b0, px} == right || py == sy || py == bottom) begin
            border = 16'hFFFF;
        end else begin
            border = fill;
        end
    end
endfunction

endmodule
