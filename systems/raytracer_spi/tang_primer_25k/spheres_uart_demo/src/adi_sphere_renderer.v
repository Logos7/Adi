module adi_sphere_renderer #(
    parameter WIDTH = 160,
    parameter HEIGHT = 80,
    parameter MAX_SPHERES = 8,
    parameter PIXEL_SCALE_Q8 = 8
)(
    input wire clk,
    input wire rst,
    input wire pixel_req,
    output reg pixel_valid,
    output reg [15:0] pixel_rgb565,
    input wire render_restart,
    input wire clear_scene,
    input wire sphere_we,
    input wire [2:0] sphere_slot,
    input wire sphere_active,
    input wire signed [15:0] sphere_cx,
    input wire signed [15:0] sphere_cy,
    input wire signed [15:0] sphere_cz,
    input wire [15:0] sphere_r,
    input wire [15:0] sphere_color
);
    reg active [0:MAX_SPHERES-1];
    reg signed [15:0] cx [0:MAX_SPHERES-1];
    reg signed [15:0] cy [0:MAX_SPHERES-1];
    reg signed [15:0] cz [0:MAX_SPHERES-1];
    reg [15:0] rr [0:MAX_SPHERES-1];
    reg [15:0] col [0:MAX_SPHERES-1];

    reg [9:0] px;
    reg [9:0] py;
    reg signed [15:0] wx;
    reg signed [15:0] wy;
    reg [3:0] state;
    reg [3:0] si;
    reg hit_any;
    reg signed [31:0] closest_t;
    reg [15:0] closest_color;
    reg [15:0] closest_z;

    reg signed [15:0] dx;
    reg signed [15:0] dy;
    reg [31:0] d2;
    reg [31:0] r2;
    reg [31:0] depth2;
    reg sqrt_start;
    wire [15:0] sqrt_root;
    wire sqrt_busy;
    wire sqrt_done;
    reg [15:0] pending_color;
    reg signed [15:0] pending_cz;

    integer i;

    adi_isqrt32 sqrt0(
        .clk(clk),
        .rst(rst),
        .start(sqrt_start),
        .radicand(depth2),
        .root(sqrt_root),
        .busy(sqrt_busy),
        .done(sqrt_done)
    );

    function [15:0] shade565;
        input [15:0] base;
        input [15:0] z;
        reg [7:0] k;
        reg [7:0] r8;
        reg [7:0] g8;
        reg [7:0] b8;
        reg [15:0] rtmp;
        reg [15:0] gtmp;
        reg [15:0] btmp;
        begin
            k = z[7:1] + 8'd64;
            if (k < 8'd48) k = 8'd48;
            r8 = {base[15:11], base[15:13]};
            g8 = {base[10:5], base[10:9]};
            b8 = {base[4:0], base[4:2]};
            rtmp = r8 * k;
            gtmp = g8 * k;
            btmp = b8 * k;
            shade565 = {rtmp[15:11], gtmp[15:10], btmp[15:11]};
        end
    endfunction

    always @(posedge clk) begin
        if (rst) begin
            px <= 0;
            py <= 0;
            wx <= 0;
            wy <= 0;
            state <= 0;
            si <= 0;
            hit_any <= 0;
            closest_t <= 32'sh7fffffff;
            closest_color <= 16'hffff;
            closest_z <= 0;
            dx <= 0;
            dy <= 0;
            d2 <= 0;
            r2 <= 0;
            depth2 <= 0;
            sqrt_start <= 0;
            pending_color <= 0;
            pending_cz <= 0;
            pixel_valid <= 0;
            pixel_rgb565 <= 16'h0000;
            for (i = 0; i < MAX_SPHERES; i = i + 1) begin
                active[i] <= 0;
                cx[i] <= 0;
                cy[i] <= 0;
                cz[i] <= 0;
                rr[i] <= 0;
                col[i] <= 16'hffff;
            end
            active[0] <= 1;
            cx[0] <= 16'sd0;
            cy[0] <= 16'sd0;
            cz[0] <= 16'sd768;
            rr[0] <= 16'd128;
            col[0] <= 16'hf986;
            active[1] <= 1;
            cx[1] <= -16'sd176;
            cy[1] <= -16'sd64;
            cz[1] <= 16'sd896;
            rr[1] <= 16'd80;
            col[1] <= 16'h07ff;
        end else begin
            sqrt_start <= 0;
            pixel_valid <= 0;

            if (render_restart) begin
                px <= 0;
                py <= 0;
            end

            if (clear_scene) begin
                for (i = 0; i < MAX_SPHERES; i = i + 1) active[i] <= 0;
            end

            if (sphere_we) begin
                active[sphere_slot] <= sphere_active;
                cx[sphere_slot] <= sphere_cx;
                cy[sphere_slot] <= sphere_cy;
                cz[sphere_slot] <= sphere_cz;
                rr[sphere_slot] <= sphere_r;
                col[sphere_slot] <= sphere_color;
            end

            case (state)
                0: begin
                    if (pixel_req) begin
                        wx <= ($signed({1'b0, px}) - (WIDTH / 2)) * PIXEL_SCALE_Q8;
                        wy <= ((HEIGHT / 2) - $signed({1'b0, py})) * PIXEL_SCALE_Q8;
                        si <= 0;
                        hit_any <= 0;
                        closest_t <= 32'sh7fffffff;
                        closest_color <= 16'h0000;
                        closest_z <= 0;
                        state <= 1;
                    end
                end
                1: begin
                    if (si >= MAX_SPHERES) begin
                        state <= 5;
                    end else if (!active[si]) begin
                        si <= si + 1;
                    end else begin
                        dx <= $signed(wx) - $signed(cx[si]);
                        dy <= $signed(wy) - $signed(cy[si]);
                        state <= 2;
                    end
                end
                2: begin
                    d2 <= dx * dx + dy * dy;
                    r2 <= rr[si] * rr[si];
                    state <= 3;
                end
                3: begin
                    if (d2 <= r2) begin
                        depth2 <= r2 - d2;
                        pending_color <= col[si];
                        pending_cz <= cz[si];
                        sqrt_start <= 1;
                        state <= 4;
                    end else begin
                        si <= si + 1;
                        state <= 1;
                    end
                end
                4: begin
                    if (sqrt_done) begin
                        if (($signed(pending_cz) - $signed({1'b0, sqrt_root})) < closest_t) begin
                            closest_t <= $signed(pending_cz) - $signed({1'b0, sqrt_root});
                            closest_color <= pending_color;
                            closest_z <= sqrt_root;
                            hit_any <= 1;
                        end
                        si <= si + 1;
                        state <= 1;
                    end
                end
                5: begin
                    if (hit_any) begin
                        pixel_rgb565 <= shade565(closest_color, closest_z);
                    end else begin
                        pixel_rgb565 <= 16'h08a2;
                    end
                    pixel_valid <= 1;
                    if (px == WIDTH - 1) begin
                        px <= 0;
                        if (py == HEIGHT - 1) py <= 0;
                        else py <= py + 1;
                    end else begin
                        px <= px + 1;
                    end
                    state <= 0;
                end
                default: state <= 0;
            endcase
        end
    end
endmodule
