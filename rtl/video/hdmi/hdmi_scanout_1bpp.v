// =============================================================================
// hdmi_scanout_1bpp.v
// HDMI RGB timing + external 1bpp framebuffer scanout. No built-in patterns.
// =============================================================================

module hdmi_scanout_1bpp #(
    parameter FB_WIDTH = 480,
    parameter FB_HEIGHT = 270,
    parameter FB_SCALE = 4,
    parameter FB_SCALE_SHIFT = 2,
    parameter FB_WORDS_PER_ROW = 15,
    parameter FB_ADDR_BITS = 13
) (
    input wire I_pxl_clk,
    input wire I_rst_n,
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
    output reg O_de,
    output reg O_hs,
    output reg O_vs,
    output reg [7:0] O_data_r,
    output reg [7:0] O_data_g,
    output reg [7:0] O_data_b,
    output reg [FB_ADDR_BITS-1:0] O_fb_addr,
    input wire [31:0] I_fb_data
);
    localparam [11:0] FB_SCALED_WIDTH = FB_WIDTH * FB_SCALE;
    localparam [11:0] FB_SCALED_HEIGHT = FB_HEIGHT * FB_SCALE;

    reg [11:0] h_cnt;
    reg [11:0] v_cnt;

    wire h_last = (h_cnt == I_h_total - 12'd1);
    wire v_last = (v_cnt == I_v_total - 12'd1);

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            h_cnt <= 12'd0;
            v_cnt <= 12'd0;
        end else if (h_last) begin
            h_cnt <= 12'd0;
            if (v_last) v_cnt <= 12'd0;
            else v_cnt <= v_cnt + 12'd1;
        end else begin
            h_cnt <= h_cnt + 12'd1;
        end
    end

    wire hs_raw = (h_cnt < I_h_sync);
    wire vs_raw = (v_cnt < I_v_sync);
    wire [11:0] active_x0 = I_h_sync + I_h_bporch;
    wire [11:0] active_y0 = I_v_sync + I_v_bporch;
    wire de_raw = (h_cnt >= active_x0) && (h_cnt < active_x0 + I_h_res) && (v_cnt >= active_y0) && (v_cnt < active_y0 + I_v_res);
    wire [11:0] sx = h_cnt - active_x0;
    wire [11:0] sy = v_cnt - active_y0;
    wire [11:0] fb_x0 = (I_h_res - FB_SCALED_WIDTH) >> 1;
    wire [11:0] fb_y0 = (I_v_res - FB_SCALED_HEIGHT) >> 1;
    wire in_fb_area_raw = de_raw && (sx >= fb_x0) && (sx < fb_x0 + FB_SCALED_WIDTH) && (sy >= fb_y0) && (sy < fb_y0 + FB_SCALED_HEIGHT);
    wire [11:0] fb_x_full = (sx - fb_x0) >> FB_SCALE_SHIFT;
    wire [11:0] fb_y_full = (sy - fb_y0) >> FB_SCALE_SHIFT;
    wire [8:0] fb_x = fb_x_full[8:0];
    wire [8:0] fb_y = fb_y_full[8:0];
    wire [FB_ADDR_BITS-1:0] fb_word_addr = (fb_y * FB_WORDS_PER_ROW) + (fb_x >> 5);
    wire [4:0] fb_bit_index = fb_x[4:0];

    reg in_fb_area_q1;
    reg in_fb_area_q2;
    reg [4:0] fb_bit_index_q1;
    reg [4:0] fb_bit_index_q2;
    reg de_q1;
    reg de_q2;
    reg hs_q1;
    reg hs_q2;
    reg vs_q1;
    reg vs_q2;

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_fb_addr <= {FB_ADDR_BITS{1'b0}};
            in_fb_area_q1 <= 1'b0;
            in_fb_area_q2 <= 1'b0;
            fb_bit_index_q1 <= 5'd0;
            fb_bit_index_q2 <= 5'd0;
            de_q1 <= 1'b0;
            de_q2 <= 1'b0;
            hs_q1 <= 1'b0;
            hs_q2 <= 1'b0;
            vs_q1 <= 1'b0;
            vs_q2 <= 1'b0;
        end else begin
            O_fb_addr <= fb_word_addr;
            in_fb_area_q1 <= in_fb_area_raw;
            fb_bit_index_q1 <= fb_bit_index;
            de_q1 <= de_raw;
            hs_q1 <= I_hs_pol ? hs_raw : ~hs_raw;
            vs_q1 <= I_vs_pol ? vs_raw : ~vs_raw;
            in_fb_area_q2 <= in_fb_area_q1;
            fb_bit_index_q2 <= fb_bit_index_q1;
            de_q2 <= de_q1;
            hs_q2 <= hs_q1;
            vs_q2 <= vs_q1;
        end
    end

    wire pixel_on = in_fb_area_q2 && I_fb_data[fb_bit_index_q2];

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_de <= 1'b0;
            O_hs <= 1'b0;
            O_vs <= 1'b0;
            O_data_r <= 8'd0;
            O_data_g <= 8'd0;
            O_data_b <= 8'd0;
        end else begin
            O_de <= de_q2;
            O_hs <= hs_q2;
            O_vs <= vs_q2;
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
