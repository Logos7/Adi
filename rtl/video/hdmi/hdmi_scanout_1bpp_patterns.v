// =============================================================================
// hdmi_scanout_1bpp_patterns.v
// HDMI RGB timing + 1bpp framebuffer scanout with preserved built-in patterns.
//
// mode 0: external packed framebuffer
// mode 1..7: local pattern generator, useful for HDMI bring-up and beauty tests
// =============================================================================

module hdmi_scanout_1bpp_patterns #(
    parameter FB_WIDTH = 64,
    parameter FB_HEIGHT = 64,
    parameter FB_SCALE = 8,
    parameter FB_SCALE_SHIFT = 3,
    parameter FB_WORDS_PER_ROW = 2
) (
    input wire I_pxl_clk,
    input wire I_rst_n,
    input wire [2:0] I_mode,
    input wire [11:0] I_h_total,
    input wire [11:0] I_h_sync,
    input wire [11:0] I_h_bporch,
    input wire [11:0] I_h_res,
    input wire [11:0] I_v_total,
    input wire [11:0] I_v_sync,
    input wire [11:0] I_v_bporch,
    input wire [11:0] I_v_res,
    input wire I_hs_pol,
    input wire I_vs_pol,
    output wire O_de,
    output reg O_hs,
    output reg O_vs,
    output reg [7:0] O_data_r,
    output reg [7:0] O_data_g,
    output reg [7:0] O_data_b,
    output reg [10:0] O_fb_addr,
    input wire [31:0] I_fb_data
);
    reg [11:0] h_cnt;
    reg [11:0] v_cnt;

    wire h_last = (h_cnt == I_h_total - 12'd1);
    wire v_last = (v_cnt == I_v_total - 12'd1);

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            h_cnt <= 12'd0;
            v_cnt <= 12'd0;
        end else begin
            if (h_last) begin
                h_cnt <= 12'd0;
                if (v_last)
                    v_cnt <= 12'd0;
                else
                    v_cnt <= v_cnt + 12'd1;
            end else begin
                h_cnt <= h_cnt + 12'd1;
            end
        end
    end

    wire hs_raw = (h_cnt < I_h_sync);
    wire vs_raw = (v_cnt < I_v_sync);

    wire [11:0] active_x0 = I_h_sync + I_h_bporch;
    wire [11:0] active_y0 = I_v_sync + I_v_bporch;

    wire de_raw =
        (h_cnt >= active_x0) &&
        (h_cnt <  active_x0 + I_h_res) &&
        (v_cnt >= active_y0) &&
        (v_cnt <  active_y0 + I_v_res);

    wire [11:0] sx = h_cnt - active_x0;
    wire [11:0] sy = v_cnt - active_y0;

    wire [11:0] fb_x0 = 12'd320;
    wire [11:0] fb_y0 = 12'd160;
    wire in_320x200 =
        de_raw &&
        (sx >= fb_x0) &&
        (sx <  fb_x0 + 12'd640) &&
        (sy >= fb_y0) &&
        (sy <  fb_y0 + 12'd400);

    wire [11:0] fb_x_full = (sx - fb_x0) >> FB_SCALE_SHIFT;
    wire [11:0] fb_y_full = (sy - fb_y0) >> FB_SCALE_SHIFT;
    wire [8:0] fb_x = fb_x_full[8:0];
    wire [7:0] fb_y = fb_y_full[7:0];
    wire [10:0] fb_word_addr = (fb_y * FB_WORDS_PER_ROW) + (fb_x >> 5);
    wire [4:0] fb_bit_index = fb_x[4:0];

    reg in_fb_area_d;
    reg [4:0] fb_bit_index_d;
    reg de_d;
    reg hs_d;
    reg vs_d;

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_fb_addr <= 11'd0;
            in_fb_area_d <= 1'b0;
            fb_bit_index_d <= 5'd0;
            de_d <= 1'b0;
            hs_d <= 1'b0;
            vs_d <= 1'b0;
        end else begin
            O_fb_addr <= fb_word_addr;
            in_fb_area_d <= in_320x200;
            fb_bit_index_d <= fb_bit_index;
            de_d <= de_raw;
            hs_d <= I_hs_pol ? hs_raw : ~hs_raw;
            vs_d <= I_vs_pol ? vs_raw : ~vs_raw;
        end
    end

    wire border =
        (fb_x == 9'd0) ||
        (fb_x == 9'd319) ||
        (fb_y == 8'd0) ||
        (fb_y == 8'd199);

    wire center_cross =
        (fb_x == 9'd160) ||
        (fb_y == 8'd100);

    wire grid =
        (fb_x[4:0] == 5'd0) ||
        (fb_y[4:0] == 5'd0);

    wire diag =
        (fb_x[7:0] == fb_y) ||
        (fb_x[7:0] == (8'd199 - fb_y));

    wire sierpinski = ((fb_x[7:0] & fb_y) == 8'd0);
    wire xor_dense = ^(fb_x[8:0] ^ {1'b0, fb_y});
    wire xor_blocks = ((fb_x[5] ^ fb_y[5]) ^ (fb_x[3] & fb_y[3]));
    wire rings = ((fb_x[7:0] * fb_x[7:0] + fb_y * fb_y) & 16'h0400) != 16'd0;

    reg pattern_on;

    always @(*) begin
        case (I_mode)
            3'd1: pattern_on = border | center_cross | diag | grid;
            3'd2: pattern_on = sierpinski;
            3'd3: pattern_on = xor_blocks;
            3'd4: pattern_on = xor_dense;
            3'd5: pattern_on = rings;
            3'd6: pattern_on = border | sierpinski;
            3'd7: pattern_on = 1'b1;
            default: pattern_on = 1'b0;
        endcase
    end

    wire fb_pixel_on = in_fb_area_d && I_fb_data[fb_bit_index_d];
    wire pattern_pixel_on = in_fb_area_d && pattern_on;
    wire pixel_on = (I_mode == 3'd0) ? fb_pixel_on : pattern_pixel_on;

    assign O_de = de_d;

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_hs <= 1'b0;
            O_vs <= 1'b0;
            O_data_r <= 8'd0;
            O_data_g <= 8'd0;
            O_data_b <= 8'd0;
        end else begin
            O_hs <= hs_d;
            O_vs <= vs_d;

            if (pixel_on) begin
                O_data_r <= 8'hff;
                O_data_g <= 8'hff;
                O_data_b <= 8'hff;
            end else begin
                O_data_r <= 8'h00;
                O_data_g <= 8'h00;
                O_data_b <= 8'h00;
            end
        end
    end
endmodule
