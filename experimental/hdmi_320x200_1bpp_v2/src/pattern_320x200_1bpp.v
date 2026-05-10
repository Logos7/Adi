module pattern_320x200_1bpp (
    input I_pxl_clk,
    input I_rst_n,
    input [2:0] I_mode,
    input [7:0] I_single_r,
    input [7:0] I_single_g,
    input [7:0] I_single_b,
    input [11:0] I_h_total,
    input [11:0] I_h_sync,
    input [11:0] I_h_bporch,
    input [11:0] I_h_res,
    input [11:0] I_v_total,
    input [11:0] I_v_sync,
    input [11:0] I_v_bporch,
    input [11:0] I_v_res,
    input I_hs_pol,
    input I_vs_pol,
    output O_de,
    output reg O_hs,
    output reg O_vs,
    output reg [7:0] O_data_r,
    output reg [7:0] O_data_g,
    output reg [7:0] O_data_b
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

wire in_320x200 =
    de_raw &&
    (sx >= 12'd320) &&
    (sx <  12'd960) &&
    (sy >= 12'd160) &&
    (sy <  12'd560);

wire [8:0] fb_x = (sx - 12'd320) >> 1;
wire [7:0] fb_y = (sy - 12'd160) >> 1;

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

reg pixel_on;

always @(*) begin
    case (I_mode)
        3'd0: pixel_on = border | center_cross | diag | grid;
        3'd1: pixel_on = sierpinski;
        3'd2: pixel_on = xor_blocks;
        3'd3: pixel_on = xor_dense;
        3'd4: pixel_on = rings;
        3'd5: pixel_on = border | sierpinski;
        3'd6: pixel_on = 1'b1;
        default: pixel_on = 1'b0;
    endcase
end

assign O_de = de_raw;

always @(posedge I_pxl_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
        O_hs <= 1'b0;
        O_vs <= 1'b0;
        O_data_r <= 8'd0;
        O_data_g <= 8'd0;
        O_data_b <= 8'd0;
    end else begin
        O_hs <= I_hs_pol ? hs_raw : ~hs_raw;
        O_vs <= I_vs_pol ? vs_raw : ~vs_raw;

        if (in_320x200 && pixel_on) begin
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
