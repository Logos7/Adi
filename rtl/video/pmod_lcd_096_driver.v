module pmod_lcd_096_driver #(
    parameter CLK_HZ = 50_000_000,
    parameter SPI_DIV = 2
)(
    input clk,
    input rst,
    input [15:0] pixel_rgb565,
    output reg [6:0] pixel_x,
    output reg [7:0] pixel_y,
    output reg frame_tick,
    output reg [15:0] frame,
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
localparam S_PIXEL_LATCH = 5'd9;
localparam S_PIXEL_HI    = 5'd10;
localparam S_PIXEL_HIW   = 5'd11;
localparam S_PIXEL_LO    = 5'd12;
localparam S_PIXEL_LOW   = 5'd13;
localparam S_FRAME_GAP   = 5'd14;

reg [4:0] state = S_RESET_0;
reg [31:0] wait_count = 32'd0;
reg [8:0] delay_left = 9'd0;
reg [6:0] init_index = 7'd0;
reg [3:0] win_index = 4'd0;
reg [15:0] pixel = 16'd0;
reg lcd_resetn_r = 1'b0;
reg spi_start = 1'b0;
reg spi_dc = 1'b0;
reg [7:0] spi_byte = 8'd0;
wire spi_busy;
wire spi_done;
wire ms_tick = wait_count == (CLK_HZ / 1000 - 1);
wire [10:0] init_entry = init_word(init_index);
wire [10:0] win_entry = window_word(win_index);

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
        pixel_x <= 7'd0;
        pixel_y <= 8'd0;
        frame_tick <= 1'b0;
        frame <= 16'd0;
        pixel <= 16'd0;
        lcd_resetn_r <= 1'b0;
        spi_start <= 1'b0;
        spi_dc <= 1'b0;
        spi_byte <= 8'd0;
    end else begin
        spi_start <= 1'b0;
        frame_tick <= 1'b0;

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
                    pixel_x <= 7'd0;
                    pixel_y <= 8'd0;
                    state <= S_PIXEL_LATCH;
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

            S_PIXEL_LATCH: begin
                pixel <= pixel_rgb565;
                state <= S_PIXEL_HI;
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
                    if (pixel_x == 7'd79 && pixel_y == 8'd159) begin
                        frame <= frame + 16'd1;
                        frame_tick <= 1'b1;
                        delay_left <= 9'd2;
                        wait_count <= 32'd0;
                        state <= S_FRAME_GAP;
                    end else begin
                        if (pixel_x == 7'd79) begin
                            pixel_x <= 7'd0;
                            pixel_y <= pixel_y + 8'd1;
                        end else begin
                            pixel_x <= pixel_x + 7'd1;
                        end
                        state <= S_PIXEL_LATCH;
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

endmodule
