// =============================================================================
// hdmi_scanout_1bpp_patterns.v
// HDMI RGB timing + external 1bpp framebuffer scanout.
//
// V12:
// - Legacy module name is kept for the existing Gowin project file.
// - Built-in patterns are removed; I_mode is ignored.
// - 480x270 is scaled exactly x4 into 1920x1080.
// - Framebuffer address generation is sequential to keep the pixel path light.
// - O_frame_start pulses during vertical blank, so the top can swap buffers
//   outside visible scanout.
// =============================================================================

module hdmi_scanout_1bpp_patterns #(
    parameter FB_WIDTH = 480,
    parameter FB_HEIGHT = 270,
    parameter FB_SCALE = 4,
    parameter FB_SCALE_SHIFT = 2,
    parameter FB_ADDR_BITS = 17
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
    output reg O_de,
    output reg O_hs,
    output reg O_vs,
    output reg [7:0] O_data_r,
    output reg [7:0] O_data_g,
    output reg [7:0] O_data_b,
    output reg [FB_ADDR_BITS-1:0] O_fb_addr,
    output reg O_frame_start,
    input wire I_fb_data
);
    wire unused_mode = |I_mode;
    wire unused_params = (FB_HEIGHT != 270) | (FB_SCALE != 4) | (FB_SCALE_SHIFT != 2);
    localparam [FB_ADDR_BITS-1:0] FB_WIDTH_ADDR = FB_WIDTH;

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
            if (v_last)
                v_cnt <= 12'd0;
            else
                v_cnt <= v_cnt + 12'd1;
        end else begin
            h_cnt <= h_cnt + 12'd1;
        end
    end

    wire hs_raw = (h_cnt < I_h_sync);
    wire vs_raw = (v_cnt < I_v_sync);
    wire [11:0] active_x0 = I_h_sync + I_h_bporch;
    wire [11:0] active_y0 = I_v_sync + I_v_bporch;
    wire active_x = (h_cnt >= active_x0) && (h_cnt < active_x0 + I_h_res);
    wire active_y = (v_cnt >= active_y0) && (v_cnt < active_y0 + I_v_res);
    wire de_raw = active_x && active_y;

    reg [8:0] fb_x;
    reg [1:0] x_phase;
    reg [1:0] y_phase;
    reg [FB_ADDR_BITS-1:0] line_base;

    wire [FB_ADDR_BITS-1:0] fb_addr_now = line_base + {{(FB_ADDR_BITS-9){1'b0}}, fb_x};

    reg de_q1;
    reg de_q2;
    reg hs_q1;
    reg hs_q2;
    reg vs_q1;
    reg vs_q2;

    always @(posedge I_pxl_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_fb_addr <= {FB_ADDR_BITS{1'b0}};
            O_frame_start <= 1'b0;
            fb_x <= 9'd0;
            x_phase <= 2'd0;
            y_phase <= 2'd0;
            line_base <= {FB_ADDR_BITS{1'b0}};
            de_q1 <= 1'b0;
            de_q2 <= 1'b0;
            hs_q1 <= 1'b0;
            hs_q2 <= 1'b0;
            vs_q1 <= 1'b0;
            vs_q2 <= 1'b0;
        end else begin
            O_frame_start <= h_last && v_last;

            if (de_raw) begin
                O_fb_addr <= fb_addr_now;
                if (x_phase == 2'd3) begin
                    x_phase <= 2'd0;
                    if (fb_x != (FB_WIDTH - 1))
                        fb_x <= fb_x + 9'd1;
                end else begin
                    x_phase <= x_phase + 2'd1;
                end
            end else begin
                O_fb_addr <= {FB_ADDR_BITS{1'b0}};
            end

            if (h_last) begin
                fb_x <= 9'd0;
                x_phase <= 2'd0;

                if (active_y) begin
                    if (y_phase == 2'd3) begin
                        y_phase <= 2'd0;
                        line_base <= line_base + FB_WIDTH_ADDR;
                    end else begin
                        y_phase <= y_phase + 2'd1;
                    end
                end

                if (v_last) begin
                    y_phase <= 2'd0;
                    line_base <= {FB_ADDR_BITS{1'b0}};
                end
            end

            de_q1 <= de_raw;
            de_q2 <= de_q1;
            hs_q1 <= I_hs_pol ? hs_raw : ~hs_raw;
            hs_q2 <= hs_q1;
            vs_q1 <= I_vs_pol ? vs_raw : ~vs_raw;
            vs_q2 <= vs_q1;
        end
    end

    wire pixel_on = de_q2 && I_fb_data;

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
                O_data_r <= 8'hFF;
                O_data_g <= 8'hFF;
                O_data_b <= 8'hFF;
            end else begin
                O_data_r <= 8'h00;
                O_data_g <= 8'h00;
                O_data_b <= 8'h00;
            end
        end
    end
endmodule
