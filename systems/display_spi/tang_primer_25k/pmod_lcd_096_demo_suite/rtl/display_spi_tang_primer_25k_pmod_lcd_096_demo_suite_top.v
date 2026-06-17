module display_spi_tang_primer_25k_pmod_lcd_096_demo_suite_top #(
    parameter CLK_HZ = 50_000_000,
    parameter SPI_DIV = 2
)(
    input clk,
    input rst,
    output lcd_resetn,
    output lcd_clk,
    output lcd_cs,
    output lcd_dc,
    output lcd_data
);

wire [6:0] x;
wire [7:0] y;
wire frame_tick;
wire [15:0] frame;
wire [15:0] colorbars_rgb;
wire [15:0] checkerboard_rgb;
wire [15:0] plasma_rgb;
wire [15:0] rings_rgb;
wire [15:0] squares_rgb;
reg [15:0] pixel_rgb;
reg [2:0] demo_select = 3'd0;
reg [8:0] demo_timer = 9'd0;

pmod_lcd_096_driver #(
    .CLK_HZ(CLK_HZ),
    .SPI_DIV(SPI_DIV)
) lcd0 (
    .clk(clk),
    .rst(rst),
    .pixel_rgb565(pixel_rgb),
    .pixel_x(x),
    .pixel_y(y),
    .frame_tick(frame_tick),
    .frame(frame),
    .lcd_resetn(lcd_resetn),
    .lcd_clk(lcd_clk),
    .lcd_cs(lcd_cs),
    .lcd_dc(lcd_dc),
    .lcd_data(lcd_data)
);

lcd_demo_colorbars colorbars0 (
    .x(x),
    .y(y),
    .frame(frame),
    .rgb565(colorbars_rgb)
);

lcd_demo_checkerboard checkerboard0 (
    .x(x),
    .y(y),
    .frame(frame),
    .rgb565(checkerboard_rgb)
);

lcd_demo_plasma plasma0 (
    .x(x),
    .y(y),
    .frame(frame),
    .rgb565(plasma_rgb)
);

lcd_demo_rings rings0 (
    .x(x),
    .y(y),
    .frame(frame),
    .rgb565(rings_rgb)
);

lcd_demo_bouncing_squares squares0 (
    .x(x),
    .y(y),
    .frame(frame),
    .rgb565(squares_rgb)
);

always @* begin
    case (demo_select)
        3'd0: pixel_rgb = colorbars_rgb;
        3'd1: pixel_rgb = checkerboard_rgb;
        3'd2: pixel_rgb = plasma_rgb;
        3'd3: pixel_rgb = rings_rgb;
        default: pixel_rgb = squares_rgb;
    endcase
end

always @(posedge clk) begin
    if (rst) begin
        demo_select <= 3'd0;
        demo_timer <= 9'd0;
    end else if (frame_tick) begin
        if (demo_timer == 9'd220) begin
            demo_timer <= 9'd0;
            if (demo_select == 3'd4) begin
                demo_select <= 3'd0;
            end else begin
                demo_select <= demo_select + 3'd1;
            end
        end else begin
            demo_timer <= demo_timer + 9'd1;
        end
    end
end

endmodule
