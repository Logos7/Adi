`timescale 1ns/1ps

module display_spi_tang_primer_25k_pmod_lcd_096_bouncing_squares_top #(
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

localparam KIND_CMD   = 2'b00;
localparam KIND_DATA  = 2'b01;
localparam KIND_DELAY = 2'b10;
localparam KIND_END   = 2'b11;

localparam S_RESET_0     = 5'd0;
localparam S_RESET_1     = 5'd1;
localparam S_INIT_FETCH  = 5'd2;
localparam S_INIT_START  = 5'd3;
localparam S_INIT_WAIT   = 5'd4;
localparam S_INIT_DELAY  = 5'd5;
localparam S_WIN_FETCH   = 5'd6;
localparam S_WIN_START   = 5'd7;
localparam S_WIN_WAIT    = 5'd8;
localparam S_PIXEL_HI    = 5'd9;
localparam S_PIXEL_HIW   = 5'd10;
localparam S_PIXEL_LO    = 5'd11;
localparam S_PIXEL_LOW   = 5'd12;
localparam S_FRAME_GAP   = 5'd13;

reg [4:0] state = S_RESET_0;
reg [31:0] wait_count = 32'd0;
reg [8:0] delay_left = 9'd0;
reg [6:0] init_index = 7'd0;
reg [3:0] win_index = 4'd0;
reg [6:0] x = 7'd0;
reg [7:0] y = 8'd0;
reg [7:0] frame = 8'd0;
reg [15:0] pixel = 16'd0;
reg lcd_resetn_r = 1'b0;
reg [7:0] sx0 = 8'd0;
reg [7:0] sy0 = 8'd0;
reg sxd0 = 1'b1;
reg syd0 = 1'b1;
reg [7:0] sx1 = 8'd68;
reg [7:0] sy1 = 8'd7;
reg sxd1 = 1'b0;
reg syd1 = 1'b1;
reg [7:0] sx2 = 8'd12;
reg [7:0] sy2 = 8'd145;
reg sxd2 = 1'b1;
reg syd2 = 1'b0;
reg [7:0] sx3 = 8'd60;
reg [7:0] sy3 = 8'd50;
reg sxd3 = 1'b0;
reg syd3 = 1'b1;
reg [7:0] sx4 = 8'd33;
reg [7:0] sy4 = 8'd20;
reg sxd4 = 1'b1;
reg syd4 = 1'b1;
reg [7:0] sx5 = 8'd45;
reg [7:0] sy5 = 8'd120;
reg sxd5 = 1'b0;
reg syd5 = 1'b0;
reg [7:0] sx6 = 8'd5;
reg [7:0] sy6 = 8'd80;
reg sxd6 = 1'b1;
reg syd6 = 1'b0;
reg [7:0] sx7 = 8'd20;
reg [7:0] sy7 = 8'd65;
reg sxd7 = 1'b1;
reg syd7 = 1'b1;
reg [7:0] sx8 = 8'd70;
reg [7:0] sy8 = 8'd150;
reg sxd8 = 1'b0;
reg syd8 = 1'b0;
reg [7:0] sx9 = 8'd55;
reg [7:0] sy9 = 8'd95;
reg sxd9 = 1'b0;
reg syd9 = 1'b1;
reg [7:0] sx10 = 8'd7;
reg [7:0] sy10 = 8'd35;
reg sxd10 = 1'b1;
reg syd10 = 1'b1;
reg [7:0] sx11 = 8'd30;
reg [7:0] sy11 = 8'd135;
reg sxd11 = 1'b1;
reg syd11 = 1'b0;
reg [7:0] sx12 = 8'd50;
reg [7:0] sy12 = 8'd10;
reg sxd12 = 1'b0;
reg syd12 = 1'b1;
reg [7:0] sx13 = 8'd74;
reg [7:0] sy13 = 8'd70;
reg sxd13 = 1'b0;
reg syd13 = 1'b1;
reg [7:0] sx14 = 8'd2;
reg [7:0] sy14 = 8'd110;
reg sxd14 = 1'b1;
reg syd14 = 1'b0;
reg [7:0] sx15 = 8'd37;
reg [7:0] sy15 = 8'd52;
reg sxd15 = 1'b0;
reg syd15 = 1'b0;
reg [7:0] sx16 = 8'd18;
reg [7:0] sy16 = 8'd8;
reg sxd16 = 1'b1;
reg syd16 = 1'b1;
reg [7:0] sx17 = 8'd66;
reg [7:0] sy17 = 8'd130;
reg sxd17 = 1'b0;
reg syd17 = 1'b0;

reg spi_start = 1'b0;
reg spi_dc = 1'b0;
reg [7:0] spi_byte = 8'd0;
wire spi_busy;
wire spi_done;

wire ms_tick = wait_count == (CLK_HZ / 1000 - 1);
wire [10:0] init_entry = init_word(init_index);
wire [10:0] win_entry = window_word(win_index);
wire [15:0] next_pixel = pixel_rgb565(x, y, frame);

assign lcd_resetn = lcd_resetn_r;

spi_lcd_master #(
    .DIVIDER(SPI_DIV)
) spi0 (
    .clk(clk),
    .rst(rst),
    .start(spi_start),
    .dc_in(spi_dc),
    .data_in(spi_byte),
    .busy(spi_busy),
    .done(spi_done),
    .sck(lcd_clk),
    .cs(lcd_cs),
    .dc(lcd_dc),
    .mosi(lcd_data)
);

always @(posedge clk) begin
    if (rst) begin
        state <= S_RESET_0;
        wait_count <= 32'd0;
        delay_left <= 9'd0;
        init_index <= 7'd0;
        win_index <= 4'd0;
        x <= 7'd0;
        y <= 8'd0;
        frame <= 8'd0;
        pixel <= 16'd0;
        lcd_resetn_r <= 1'b0;
        spi_start <= 1'b0;
        spi_dc <= 1'b0;
        spi_byte <= 8'd0;
        sx0 <= 8'd0;
        sy0 <= 8'd0;
        sxd0 <= 1'b1;
        syd0 <= 1'b1;
        sx1 <= 8'd68;
        sy1 <= 8'd7;
        sxd1 <= 1'b0;
        syd1 <= 1'b1;
        sx2 <= 8'd12;
        sy2 <= 8'd145;
        sxd2 <= 1'b1;
        syd2 <= 1'b0;
        sx3 <= 8'd60;
        sy3 <= 8'd50;
        sxd3 <= 1'b0;
        syd3 <= 1'b1;
        sx4 <= 8'd33;
        sy4 <= 8'd20;
        sxd4 <= 1'b1;
        syd4 <= 1'b1;
        sx5 <= 8'd45;
        sy5 <= 8'd120;
        sxd5 <= 1'b0;
        syd5 <= 1'b0;
        sx6 <= 8'd5;
        sy6 <= 8'd80;
        sxd6 <= 1'b1;
        syd6 <= 1'b0;
        sx7 <= 8'd20;
        sy7 <= 8'd65;
        sxd7 <= 1'b1;
        syd7 <= 1'b1;
        sx8 <= 8'd70;
        sy8 <= 8'd150;
        sxd8 <= 1'b0;
        syd8 <= 1'b0;
        sx9 <= 8'd55;
        sy9 <= 8'd95;
        sxd9 <= 1'b0;
        syd9 <= 1'b1;
        sx10 <= 8'd7;
        sy10 <= 8'd35;
        sxd10 <= 1'b1;
        syd10 <= 1'b1;
        sx11 <= 8'd30;
        sy11 <= 8'd135;
        sxd11 <= 1'b1;
        syd11 <= 1'b0;
        sx12 <= 8'd50;
        sy12 <= 8'd10;
        sxd12 <= 1'b0;
        syd12 <= 1'b1;
        sx13 <= 8'd74;
        sy13 <= 8'd70;
        sxd13 <= 1'b0;
        syd13 <= 1'b1;
        sx14 <= 8'd2;
        sy14 <= 8'd110;
        sxd14 <= 1'b1;
        syd14 <= 1'b0;
        sx15 <= 8'd37;
        sy15 <= 8'd52;
        sxd15 <= 1'b0;
        syd15 <= 1'b0;
        sx16 <= 8'd18;
        sy16 <= 8'd8;
        sxd16 <= 1'b1;
        syd16 <= 1'b1;
        sx17 <= 8'd66;
        sy17 <= 8'd130;
        sxd17 <= 1'b0;
        syd17 <= 1'b0;
    end else begin
        spi_start <= 1'b0;

        case (state)
            S_RESET_0: begin
                lcd_resetn_r <= 1'b0;
                if (ms_tick) begin
                    wait_count <= 32'd0;
                    if (delay_left == 9'd49) begin
                        delay_left <= 9'd0;
                        state <= S_RESET_1;
                    end else begin
                        delay_left <= delay_left + 9'd1;
                    end
                end else begin
                    wait_count <= wait_count + 32'd1;
                end
            end

            S_RESET_1: begin
                lcd_resetn_r <= 1'b1;
                if (ms_tick) begin
                    wait_count <= 32'd0;
                    if (delay_left == 9'd149) begin
                        delay_left <= 9'd0;
                        init_index <= 7'd0;
                        state <= S_INIT_FETCH;
                    end else begin
                        delay_left <= delay_left + 9'd1;
                    end
                end else begin
                    wait_count <= wait_count + 32'd1;
                end
            end

            S_INIT_FETCH: begin
                if (init_entry[10:9] == KIND_CMD) begin
                    spi_dc <= 1'b0;
                    spi_byte <= init_entry[7:0];
                    state <= S_INIT_START;
                end else if (init_entry[10:9] == KIND_DATA) begin
                    spi_dc <= 1'b1;
                    spi_byte <= init_entry[7:0];
                    state <= S_INIT_START;
                end else if (init_entry[10:9] == KIND_DELAY) begin
                    delay_left <= init_entry[8:0];
                    wait_count <= 32'd0;
                    state <= S_INIT_DELAY;
                end else begin
                    win_index <= 4'd0;
                    state <= S_WIN_FETCH;
                end
            end

            S_INIT_START: begin
                if (!spi_busy) begin
                    spi_start <= 1'b1;
                    state <= S_INIT_WAIT;
                end
            end

            S_INIT_WAIT: begin
                if (spi_done) begin
                    init_index <= init_index + 7'd1;
                    state <= S_INIT_FETCH;
                end
            end

            S_INIT_DELAY: begin
                if (delay_left == 9'd0) begin
                    init_index <= init_index + 7'd1;
                    state <= S_INIT_FETCH;
                end else if (ms_tick) begin
                    wait_count <= 32'd0;
                    delay_left <= delay_left - 9'd1;
                end else begin
                    wait_count <= wait_count + 32'd1;
                end
            end

            S_WIN_FETCH: begin
                if (win_entry[10:9] == KIND_CMD) begin
                    spi_dc <= 1'b0;
                    spi_byte <= win_entry[7:0];
                    state <= S_WIN_START;
                end else if (win_entry[10:9] == KIND_DATA) begin
                    spi_dc <= 1'b1;
                    spi_byte <= win_entry[7:0];
                    state <= S_WIN_START;
                end else begin
                    x <= 7'd0;
                    y <= 8'd0;
                    pixel <= pixel_rgb565(7'd0, 8'd0, frame);
                    state <= S_PIXEL_HI;
                end
            end

            S_WIN_START: begin
                if (!spi_busy) begin
                    spi_start <= 1'b1;
                    state <= S_WIN_WAIT;
                end
            end

            S_WIN_WAIT: begin
                if (spi_done) begin
                    win_index <= win_index + 4'd1;
                    state <= S_WIN_FETCH;
                end
            end

            S_PIXEL_HI: begin
                if (!spi_busy) begin
                    spi_dc <= 1'b1;
                    spi_byte <= pixel[15:8];
                    spi_start <= 1'b1;
                    state <= S_PIXEL_HIW;
                end
            end

            S_PIXEL_HIW: begin
                if (spi_done) begin
                    state <= S_PIXEL_LO;
                end
            end

            S_PIXEL_LO: begin
                if (!spi_busy) begin
                    spi_dc <= 1'b1;
                    spi_byte <= pixel[7:0];
                    spi_start <= 1'b1;
                    state <= S_PIXEL_LOW;
                end
            end

            S_PIXEL_LOW: begin
                if (spi_done) begin
                    if (x == 7'd79 && y == 8'd159) begin
                        frame <= frame + 8'd1;
                        if (sxd0) begin
                            if (sx0 + 8'd2 >= 8'd70) begin
                                sx0 <= 8'd70;
                                sxd0 <= 1'b0;
                            end else begin
                                sx0 <= sx0 + 8'd2;
                            end
                        end else begin
                            if (sx0 <= 8'd2) begin
                                sx0 <= 8'd0;
                                sxd0 <= 1'b1;
                            end else begin
                                sx0 <= sx0 - 8'd2;
                            end
                        end
                        if (syd0) begin
                            if (sy0 + 8'd3 >= 8'd150) begin
                                sy0 <= 8'd150;
                                syd0 <= 1'b0;
                            end else begin
                                sy0 <= sy0 + 8'd3;
                            end
                        end else begin
                            if (sy0 <= 8'd3) begin
                                sy0 <= 8'd0;
                                syd0 <= 1'b1;
                            end else begin
                                sy0 <= sy0 - 8'd3;
                            end
                        end
                        if (sxd1) begin
                            if (sx1 + 8'd3 >= 8'd68) begin
                                sx1 <= 8'd68;
                                sxd1 <= 1'b0;
                            end else begin
                                sx1 <= sx1 + 8'd3;
                            end
                        end else begin
                            if (sx1 <= 8'd3) begin
                                sx1 <= 8'd0;
                                sxd1 <= 1'b1;
                            end else begin
                                sx1 <= sx1 - 8'd3;
                            end
                        end
                        if (syd1) begin
                            if (sy1 + 8'd2 >= 8'd148) begin
                                sy1 <= 8'd148;
                                syd1 <= 1'b0;
                            end else begin
                                sy1 <= sy1 + 8'd2;
                            end
                        end else begin
                            if (sy1 <= 8'd2) begin
                                sy1 <= 8'd0;
                                syd1 <= 1'b1;
                            end else begin
                                sy1 <= sy1 - 8'd2;
                            end
                        end
                        if (sxd2) begin
                            if (sx2 + 8'd1 >= 8'd72) begin
                                sx2 <= 8'd72;
                                sxd2 <= 1'b0;
                            end else begin
                                sx2 <= sx2 + 8'd1;
                            end
                        end else begin
                            if (sx2 <= 8'd1) begin
                                sx2 <= 8'd0;
                                sxd2 <= 1'b1;
                            end else begin
                                sx2 <= sx2 - 8'd1;
                            end
                        end
                        if (syd2) begin
                            if (sy2 + 8'd4 >= 8'd152) begin
                                sy2 <= 8'd152;
                                syd2 <= 1'b0;
                            end else begin
                                sy2 <= sy2 + 8'd4;
                            end
                        end else begin
                            if (sy2 <= 8'd4) begin
                                sy2 <= 8'd0;
                                syd2 <= 1'b1;
                            end else begin
                                sy2 <= sy2 - 8'd4;
                            end
                        end
                        if (sxd3) begin
                            if (sx3 + 8'd2 >= 8'd66) begin
                                sx3 <= 8'd66;
                                sxd3 <= 1'b0;
                            end else begin
                                sx3 <= sx3 + 8'd2;
                            end
                        end else begin
                            if (sx3 <= 8'd2) begin
                                sx3 <= 8'd0;
                                sxd3 <= 1'b1;
                            end else begin
                                sx3 <= sx3 - 8'd2;
                            end
                        end
                        if (syd3) begin
                            if (sy3 + 8'd1 >= 8'd146) begin
                                sy3 <= 8'd146;
                                syd3 <= 1'b0;
                            end else begin
                                sy3 <= sy3 + 8'd1;
                            end
                        end else begin
                            if (sy3 <= 8'd1) begin
                                sy3 <= 8'd0;
                                syd3 <= 1'b1;
                            end else begin
                                sy3 <= sy3 - 8'd1;
                            end
                        end
                        if (sxd4) begin
                            if (sx4 + 8'd3 >= 8'd71) begin
                                sx4 <= 8'd71;
                                sxd4 <= 1'b0;
                            end else begin
                                sx4 <= sx4 + 8'd3;
                            end
                        end else begin
                            if (sx4 <= 8'd3) begin
                                sx4 <= 8'd0;
                                sxd4 <= 1'b1;
                            end else begin
                                sx4 <= sx4 - 8'd3;
                            end
                        end
                        if (syd4) begin
                            if (sy4 + 8'd3 >= 8'd151) begin
                                sy4 <= 8'd151;
                                syd4 <= 1'b0;
                            end else begin
                                sy4 <= sy4 + 8'd3;
                            end
                        end else begin
                            if (sy4 <= 8'd3) begin
                                sy4 <= 8'd0;
                                syd4 <= 1'b1;
                            end else begin
                                sy4 <= sy4 - 8'd3;
                            end
                        end
                        if (sxd5) begin
                            if (sx5 + 8'd2 >= 8'd69) begin
                                sx5 <= 8'd69;
                                sxd5 <= 1'b0;
                            end else begin
                                sx5 <= sx5 + 8'd2;
                            end
                        end else begin
                            if (sx5 <= 8'd2) begin
                                sx5 <= 8'd0;
                                sxd5 <= 1'b1;
                            end else begin
                                sx5 <= sx5 - 8'd2;
                            end
                        end
                        if (syd5) begin
                            if (sy5 + 8'd2 >= 8'd149) begin
                                sy5 <= 8'd149;
                                syd5 <= 1'b0;
                            end else begin
                                sy5 <= sy5 + 8'd2;
                            end
                        end else begin
                            if (sy5 <= 8'd2) begin
                                sy5 <= 8'd0;
                                syd5 <= 1'b1;
                            end else begin
                                sy5 <= sy5 - 8'd2;
                            end
                        end
                        if (sxd6) begin
                            if (sx6 + 8'd4 >= 8'd73) begin
                                sx6 <= 8'd73;
                                sxd6 <= 1'b0;
                            end else begin
                                sx6 <= sx6 + 8'd4;
                            end
                        end else begin
                            if (sx6 <= 8'd4) begin
                                sx6 <= 8'd0;
                                sxd6 <= 1'b1;
                            end else begin
                                sx6 <= sx6 - 8'd4;
                            end
                        end
                        if (syd6) begin
                            if (sy6 + 8'd3 >= 8'd153) begin
                                sy6 <= 8'd153;
                                syd6 <= 1'b0;
                            end else begin
                                sy6 <= sy6 + 8'd3;
                            end
                        end else begin
                            if (sy6 <= 8'd3) begin
                                sy6 <= 8'd0;
                                syd6 <= 1'b1;
                            end else begin
                                sy6 <= sy6 - 8'd3;
                            end
                        end
                        if (sxd7) begin
                            if (sx7 + 8'd1 >= 8'd67) begin
                                sx7 <= 8'd67;
                                sxd7 <= 1'b0;
                            end else begin
                                sx7 <= sx7 + 8'd1;
                            end
                        end else begin
                            if (sx7 <= 8'd1) begin
                                sx7 <= 8'd0;
                                sxd7 <= 1'b1;
                            end else begin
                                sx7 <= sx7 - 8'd1;
                            end
                        end
                        if (syd7) begin
                            if (sy7 + 8'd2 >= 8'd147) begin
                                sy7 <= 8'd147;
                                syd7 <= 1'b0;
                            end else begin
                                sy7 <= sy7 + 8'd2;
                            end
                        end else begin
                            if (sy7 <= 8'd2) begin
                                sy7 <= 8'd0;
                                syd7 <= 1'b1;
                            end else begin
                                sy7 <= sy7 - 8'd2;
                            end
                        end
                        if (sxd8) begin
                            if (sx8 + 8'd2 >= 8'd70) begin
                                sx8 <= 8'd70;
                                sxd8 <= 1'b0;
                            end else begin
                                sx8 <= sx8 + 8'd2;
                            end
                        end else begin
                            if (sx8 <= 8'd2) begin
                                sx8 <= 8'd0;
                                sxd8 <= 1'b1;
                            end else begin
                                sx8 <= sx8 - 8'd2;
                            end
                        end
                        if (syd8) begin
                            if (sy8 + 8'd4 >= 8'd150) begin
                                sy8 <= 8'd150;
                                syd8 <= 1'b0;
                            end else begin
                                sy8 <= sy8 + 8'd4;
                            end
                        end else begin
                            if (sy8 <= 8'd4) begin
                                sy8 <= 8'd0;
                                syd8 <= 1'b1;
                            end else begin
                                sy8 <= sy8 - 8'd4;
                            end
                        end
                        if (sxd9) begin
                            if (sx9 + 8'd3 >= 8'd72) begin
                                sx9 <= 8'd72;
                                sxd9 <= 1'b0;
                            end else begin
                                sx9 <= sx9 + 8'd3;
                            end
                        end else begin
                            if (sx9 <= 8'd3) begin
                                sx9 <= 8'd0;
                                sxd9 <= 1'b1;
                            end else begin
                                sx9 <= sx9 - 8'd3;
                            end
                        end
                        if (syd9) begin
                            if (sy9 + 8'd1 >= 8'd152) begin
                                sy9 <= 8'd152;
                                syd9 <= 1'b0;
                            end else begin
                                sy9 <= sy9 + 8'd1;
                            end
                        end else begin
                            if (sy9 <= 8'd1) begin
                                sy9 <= 8'd0;
                                syd9 <= 1'b1;
                            end else begin
                                sy9 <= sy9 - 8'd1;
                            end
                        end
                        if (sxd10) begin
                            if (sx10 + 8'd2 >= 8'd68) begin
                                sx10 <= 8'd68;
                                sxd10 <= 1'b0;
                            end else begin
                                sx10 <= sx10 + 8'd2;
                            end
                        end else begin
                            if (sx10 <= 8'd2) begin
                                sx10 <= 8'd0;
                                sxd10 <= 1'b1;
                            end else begin
                                sx10 <= sx10 - 8'd2;
                            end
                        end
                        if (syd10) begin
                            if (sy10 + 8'd2 >= 8'd148) begin
                                sy10 <= 8'd148;
                                syd10 <= 1'b0;
                            end else begin
                                sy10 <= sy10 + 8'd2;
                            end
                        end else begin
                            if (sy10 <= 8'd2) begin
                                sy10 <= 8'd0;
                                syd10 <= 1'b1;
                            end else begin
                                sy10 <= sy10 - 8'd2;
                            end
                        end
                        if (sxd11) begin
                            if (sx11 + 8'd4 >= 8'd71) begin
                                sx11 <= 8'd71;
                                sxd11 <= 1'b0;
                            end else begin
                                sx11 <= sx11 + 8'd4;
                            end
                        end else begin
                            if (sx11 <= 8'd4) begin
                                sx11 <= 8'd0;
                                sxd11 <= 1'b1;
                            end else begin
                                sx11 <= sx11 - 8'd4;
                            end
                        end
                        if (syd11) begin
                            if (sy11 + 8'd1 >= 8'd151) begin
                                sy11 <= 8'd151;
                                syd11 <= 1'b0;
                            end else begin
                                sy11 <= sy11 + 8'd1;
                            end
                        end else begin
                            if (sy11 <= 8'd1) begin
                                sy11 <= 8'd0;
                                syd11 <= 1'b1;
                            end else begin
                                sy11 <= sy11 - 8'd1;
                            end
                        end
                        if (sxd12) begin
                            if (sx12 + 8'd1 >= 8'd65) begin
                                sx12 <= 8'd65;
                                sxd12 <= 1'b0;
                            end else begin
                                sx12 <= sx12 + 8'd1;
                            end
                        end else begin
                            if (sx12 <= 8'd1) begin
                                sx12 <= 8'd0;
                                sxd12 <= 1'b1;
                            end else begin
                                sx12 <= sx12 - 8'd1;
                            end
                        end
                        if (syd12) begin
                            if (sy12 + 8'd3 >= 8'd145) begin
                                sy12 <= 8'd145;
                                syd12 <= 1'b0;
                            end else begin
                                sy12 <= sy12 + 8'd3;
                            end
                        end else begin
                            if (sy12 <= 8'd3) begin
                                sy12 <= 8'd0;
                                syd12 <= 1'b1;
                            end else begin
                                sy12 <= sy12 - 8'd3;
                            end
                        end
                        if (sxd13) begin
                            if (sx13 + 8'd2 >= 8'd74) begin
                                sx13 <= 8'd74;
                                sxd13 <= 1'b0;
                            end else begin
                                sx13 <= sx13 + 8'd2;
                            end
                        end else begin
                            if (sx13 <= 8'd2) begin
                                sx13 <= 8'd0;
                                sxd13 <= 1'b1;
                            end else begin
                                sx13 <= sx13 - 8'd2;
                            end
                        end
                        if (syd13) begin
                            if (sy13 + 8'd4 >= 8'd154) begin
                                sy13 <= 8'd154;
                                syd13 <= 1'b0;
                            end else begin
                                sy13 <= sy13 + 8'd4;
                            end
                        end else begin
                            if (sy13 <= 8'd4) begin
                                sy13 <= 8'd0;
                                syd13 <= 1'b1;
                            end else begin
                                sy13 <= sy13 - 8'd4;
                            end
                        end
                        if (sxd14) begin
                            if (sx14 + 8'd3 >= 8'd69) begin
                                sx14 <= 8'd69;
                                sxd14 <= 1'b0;
                            end else begin
                                sx14 <= sx14 + 8'd3;
                            end
                        end else begin
                            if (sx14 <= 8'd3) begin
                                sx14 <= 8'd0;
                                sxd14 <= 1'b1;
                            end else begin
                                sx14 <= sx14 - 8'd3;
                            end
                        end
                        if (syd14) begin
                            if (sy14 + 8'd2 >= 8'd149) begin
                                sy14 <= 8'd149;
                                syd14 <= 1'b0;
                            end else begin
                                sy14 <= sy14 + 8'd2;
                            end
                        end else begin
                            if (sy14 <= 8'd2) begin
                                sy14 <= 8'd0;
                                syd14 <= 1'b1;
                            end else begin
                                sy14 <= sy14 - 8'd2;
                            end
                        end
                        if (sxd15) begin
                            if (sx15 + 8'd1 >= 8'd72) begin
                                sx15 <= 8'd72;
                                sxd15 <= 1'b0;
                            end else begin
                                sx15 <= sx15 + 8'd1;
                            end
                        end else begin
                            if (sx15 <= 8'd1) begin
                                sx15 <= 8'd0;
                                sxd15 <= 1'b1;
                            end else begin
                                sx15 <= sx15 - 8'd1;
                            end
                        end
                        if (syd15) begin
                            if (sy15 + 8'd3 >= 8'd152) begin
                                sy15 <= 8'd152;
                                syd15 <= 1'b0;
                            end else begin
                                sy15 <= sy15 + 8'd3;
                            end
                        end else begin
                            if (sy15 <= 8'd3) begin
                                sy15 <= 8'd0;
                                syd15 <= 1'b1;
                            end else begin
                                sy15 <= sy15 - 8'd3;
                            end
                        end
                        if (sxd16) begin
                            if (sx16 + 8'd2 >= 8'd70) begin
                                sx16 <= 8'd70;
                                sxd16 <= 1'b0;
                            end else begin
                                sx16 <= sx16 + 8'd2;
                            end
                        end else begin
                            if (sx16 <= 8'd2) begin
                                sx16 <= 8'd0;
                                sxd16 <= 1'b1;
                            end else begin
                                sx16 <= sx16 - 8'd2;
                            end
                        end
                        if (syd16) begin
                            if (sy16 + 8'd4 >= 8'd150) begin
                                sy16 <= 8'd150;
                                syd16 <= 1'b0;
                            end else begin
                                sy16 <= sy16 + 8'd4;
                            end
                        end else begin
                            if (sy16 <= 8'd4) begin
                                sy16 <= 8'd0;
                                syd16 <= 1'b1;
                            end else begin
                                sy16 <= sy16 - 8'd4;
                            end
                        end
                        if (sxd17) begin
                            if (sx17 + 8'd3 >= 8'd68) begin
                                sx17 <= 8'd68;
                                sxd17 <= 1'b0;
                            end else begin
                                sx17 <= sx17 + 8'd3;
                            end
                        end else begin
                            if (sx17 <= 8'd3) begin
                                sx17 <= 8'd0;
                                sxd17 <= 1'b1;
                            end else begin
                                sx17 <= sx17 - 8'd3;
                            end
                        end
                        if (syd17) begin
                            if (sy17 + 8'd3 >= 8'd148) begin
                                sy17 <= 8'd148;
                                syd17 <= 1'b0;
                            end else begin
                                sy17 <= sy17 + 8'd3;
                            end
                        end else begin
                            if (sy17 <= 8'd3) begin
                                sy17 <= 8'd0;
                                syd17 <= 1'b1;
                            end else begin
                                sy17 <= sy17 - 8'd3;
                            end
                        end
                        delay_left <= 9'd2;
                        wait_count <= 32'd0;
                        state <= S_FRAME_GAP;
                    end else begin
                        if (x == 7'd79) begin
                            x <= 7'd0;
                            y <= y + 8'd1;
                            pixel <= pixel_rgb565(7'd0, y + 8'd1, frame);
                        end else begin
                            x <= x + 7'd1;
                            pixel <= pixel_rgb565(x + 7'd1, y, frame);
                        end
                        state <= S_PIXEL_HI;
                    end
                end
            end

            S_FRAME_GAP: begin
                if (delay_left == 9'd0) begin
                    win_index <= 4'd0;
                    state <= S_WIN_FETCH;
                end else if (ms_tick) begin
                    wait_count <= 32'd0;
                    delay_left <= delay_left - 9'd1;
                end else begin
                    wait_count <= wait_count + 32'd1;
                end
            end

            default: begin
                state <= S_RESET_0;
            end
        endcase
    end
end

function [10:0] ew_cmd;
    input [7:0] v;
    begin
        ew_cmd = {KIND_CMD, 1'b0, v};
    end
endfunction

function [10:0] ew_data;
    input [7:0] v;
    begin
        ew_data = {KIND_DATA, 1'b0, v};
    end
endfunction

function [10:0] ew_delay;
    input [8:0] v;
    begin
        ew_delay = {KIND_DELAY, v};
    end
endfunction

function [10:0] ew_end;
    input dummy;
    begin
        ew_end = {KIND_END, 9'd0};
    end
endfunction

function [10:0] init_word;
    input [6:0] i;
    begin
        case (i)
            7'd0: init_word = ew_cmd(8'h01);
            7'd1: init_word = ew_delay(9'd150);
            7'd2: init_word = ew_cmd(8'h11);
            7'd3: init_word = ew_delay(9'd120);
            7'd4: init_word = ew_cmd(8'hB1);
            7'd5: init_word = ew_data(8'h05);
            7'd6: init_word = ew_data(8'h3C);
            7'd7: init_word = ew_data(8'h3C);
            7'd8: init_word = ew_cmd(8'hB2);
            7'd9: init_word = ew_data(8'h05);
            7'd10: init_word = ew_data(8'h3C);
            7'd11: init_word = ew_data(8'h3C);
            7'd12: init_word = ew_cmd(8'hB3);
            7'd13: init_word = ew_data(8'h05);
            7'd14: init_word = ew_data(8'h3C);
            7'd15: init_word = ew_data(8'h3C);
            7'd16: init_word = ew_data(8'h05);
            7'd17: init_word = ew_data(8'h3C);
            7'd18: init_word = ew_data(8'h3C);
            7'd19: init_word = ew_cmd(8'hB4);
            7'd20: init_word = ew_data(8'h03);
            7'd21: init_word = ew_cmd(8'hC0);
            7'd22: init_word = ew_data(8'hAB);
            7'd23: init_word = ew_data(8'h0B);
            7'd24: init_word = ew_data(8'h04);
            7'd25: init_word = ew_cmd(8'hC1);
            7'd26: init_word = ew_data(8'hC5);
            7'd27: init_word = ew_cmd(8'hC2);
            7'd28: init_word = ew_data(8'h0D);
            7'd29: init_word = ew_data(8'h00);
            7'd30: init_word = ew_cmd(8'hC3);
            7'd31: init_word = ew_data(8'h8D);
            7'd32: init_word = ew_data(8'h6A);
            7'd33: init_word = ew_cmd(8'hC4);
            7'd34: init_word = ew_data(8'h8D);
            7'd35: init_word = ew_data(8'hEE);
            7'd36: init_word = ew_cmd(8'hC5);
            7'd37: init_word = ew_data(8'h0F);
            7'd38: init_word = ew_cmd(8'hE0);
            7'd39: init_word = ew_data(8'h07);
            7'd40: init_word = ew_data(8'h0E);
            7'd41: init_word = ew_data(8'h08);
            7'd42: init_word = ew_data(8'h07);
            7'd43: init_word = ew_data(8'h10);
            7'd44: init_word = ew_data(8'h07);
            7'd45: init_word = ew_data(8'h02);
            7'd46: init_word = ew_data(8'h07);
            7'd47: init_word = ew_data(8'h09);
            7'd48: init_word = ew_data(8'h0F);
            7'd49: init_word = ew_data(8'h25);
            7'd50: init_word = ew_data(8'h36);
            7'd51: init_word = ew_data(8'h00);
            7'd52: init_word = ew_data(8'h08);
            7'd53: init_word = ew_data(8'h04);
            7'd54: init_word = ew_data(8'h10);
            7'd55: init_word = ew_cmd(8'hE1);
            7'd56: init_word = ew_data(8'h0A);
            7'd57: init_word = ew_data(8'h0D);
            7'd58: init_word = ew_data(8'h08);
            7'd59: init_word = ew_data(8'h07);
            7'd60: init_word = ew_data(8'h0F);
            7'd61: init_word = ew_data(8'h07);
            7'd62: init_word = ew_data(8'h02);
            7'd63: init_word = ew_data(8'h07);
            7'd64: init_word = ew_data(8'h09);
            7'd65: init_word = ew_data(8'h0F);
            7'd66: init_word = ew_data(8'h25);
            7'd67: init_word = ew_data(8'h35);
            7'd68: init_word = ew_data(8'h00);
            7'd69: init_word = ew_data(8'h09);
            7'd70: init_word = ew_data(8'h04);
            7'd71: init_word = ew_data(8'h10);
            7'd72: init_word = ew_cmd(8'hFC);
            7'd73: init_word = ew_data(8'h80);
            7'd74: init_word = ew_cmd(8'h3A);
            7'd75: init_word = ew_data(8'h05);
            7'd76: init_word = ew_cmd(8'h36);
            7'd77: init_word = ew_data(8'h08);
            7'd78: init_word = ew_cmd(8'h21);
            7'd79: init_word = ew_cmd(8'h29);
            7'd80: init_word = ew_delay(9'd50);
            default: init_word = ew_end(1'b0);
        endcase
    end
endfunction

function [10:0] window_word;
    input [3:0] i;
    begin
        case (i)
            4'd0: window_word = ew_cmd(8'h2A);
            4'd1: window_word = ew_data(8'h00);
            4'd2: window_word = ew_data(8'h1A);
            4'd3: window_word = ew_data(8'h00);
            4'd4: window_word = ew_data(8'h69);
            4'd5: window_word = ew_cmd(8'h2B);
            4'd6: window_word = ew_data(8'h00);
            4'd7: window_word = ew_data(8'h01);
            4'd8: window_word = ew_data(8'h00);
            4'd9: window_word = ew_data(8'hA0);
            4'd10: window_word = ew_cmd(8'h2C);
            default: window_word = ew_end(1'b0);
        endcase
    end
endfunction

function is_inside_square;
    input [6:0] px;
    input [7:0] py;
    input [7:0] sx;
    input [7:0] sy;
    input [4:0] size;
    reg [7:0] right;
    reg [7:0] bottom;
    begin
        right = sx + {3'd0, size} - 8'd1;
        bottom = sy + {3'd0, size} - 8'd1;
        is_inside_square = (px >= sx[6:0]) && (px <= right[6:0]) && (py >= sy) && (py <= bottom);
    end
endfunction

function [15:0] square_pixel;
    input [6:0] px;
    input [7:0] py;
    input [7:0] sx;
    input [7:0] sy;
    input [4:0] size;
    input [15:0] fill;
    reg [7:0] right;
    reg [7:0] bottom;
    begin
        right = sx + {3'd0, size} - 8'd1;
        bottom = sy + {3'd0, size} - 8'd1;
        if (px == sx[6:0] || px == right[6:0] || py == sy || py == bottom) begin
            square_pixel = 16'hFFFF;
        end else begin
            square_pixel = fill;
        end
    end
endfunction

function [15:0] pixel_rgb565;
    input [6:0] px;
    input [7:0] py;
    input [7:0] t;
    begin
        pixel_rgb565 = 16'h0000;
        if (is_inside_square(px, py, sx0, sy0, 5'd10)) begin
            pixel_rgb565 = square_pixel(px, py, sx0, sy0, 5'd10, 16'hF800);
        end
        else if (is_inside_square(px, py, sx1, sy1, 5'd12)) begin
            pixel_rgb565 = square_pixel(px, py, sx1, sy1, 5'd12, 16'h07E0);
        end
        else if (is_inside_square(px, py, sx2, sy2, 5'd8)) begin
            pixel_rgb565 = square_pixel(px, py, sx2, sy2, 5'd8, 16'h001F);
        end
        else if (is_inside_square(px, py, sx3, sy3, 5'd14)) begin
            pixel_rgb565 = square_pixel(px, py, sx3, sy3, 5'd14, 16'hFFE0);
        end
        else if (is_inside_square(px, py, sx4, sy4, 5'd9)) begin
            pixel_rgb565 = square_pixel(px, py, sx4, sy4, 5'd9, 16'hF81F);
        end
        else if (is_inside_square(px, py, sx5, sy5, 5'd11)) begin
            pixel_rgb565 = square_pixel(px, py, sx5, sy5, 5'd11, 16'h07FF);
        end
        else if (is_inside_square(px, py, sx6, sy6, 5'd7)) begin
            pixel_rgb565 = square_pixel(px, py, sx6, sy6, 5'd7, 16'hFD20);
        end
        else if (is_inside_square(px, py, sx7, sy7, 5'd13)) begin
            pixel_rgb565 = square_pixel(px, py, sx7, sy7, 5'd13, 16'hFC1F);
        end
        else if (is_inside_square(px, py, sx8, sy8, 5'd10)) begin
            pixel_rgb565 = square_pixel(px, py, sx8, sy8, 5'd10, 16'h841F);
        end
        else if (is_inside_square(px, py, sx9, sy9, 5'd8)) begin
            pixel_rgb565 = square_pixel(px, py, sx9, sy9, 5'd8, 16'h87E0);
        end
        else if (is_inside_square(px, py, sx10, sy10, 5'd12)) begin
            pixel_rgb565 = square_pixel(px, py, sx10, sy10, 5'd12, 16'h05FF);
        end
        else if (is_inside_square(px, py, sx11, sy11, 5'd9)) begin
            pixel_rgb565 = square_pixel(px, py, sx11, sy11, 5'd9, 16'hFBE0);
        end
        else if (is_inside_square(px, py, sx12, sy12, 5'd15)) begin
            pixel_rgb565 = square_pixel(px, py, sx12, sy12, 5'd15, 16'hA145);
        end
        else if (is_inside_square(px, py, sx13, sy13, 5'd6)) begin
            pixel_rgb565 = square_pixel(px, py, sx13, sy13, 5'd6, 16'h7FE0);
        end
        else if (is_inside_square(px, py, sx14, sy14, 5'd11)) begin
            pixel_rgb565 = square_pixel(px, py, sx14, sy14, 5'd11, 16'hF81C);
        end
        else if (is_inside_square(px, py, sx15, sy15, 5'd8)) begin
            pixel_rgb565 = square_pixel(px, py, sx15, sy15, 5'd8, 16'h07F0);
        end
        else if (is_inside_square(px, py, sx16, sy16, 5'd10)) begin
            pixel_rgb565 = square_pixel(px, py, sx16, sy16, 5'd10, 16'hFDBF);
        end
        else if (is_inside_square(px, py, sx17, sy17, 5'd12)) begin
            pixel_rgb565 = square_pixel(px, py, sx17, sy17, 5'd12, 16'h9CFF);
        end
        else begin
            pixel_rgb565 = 16'h0000;
        end
    end
endfunction

endmodule
