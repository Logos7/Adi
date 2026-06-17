module adi_isqrt32(
    input wire clk,
    input wire rst,
    input wire start,
    input wire [31:0] radicand,
    output reg [15:0] root,
    output reg busy,
    output reg done
);
    reg [31:0] x;
    reg [31:0] rem;
    reg [15:0] res;
    reg [4:0] iter;
    reg [33:0] trial;

    always @(posedge clk) begin
        if (rst) begin
            x <= 0;
            rem <= 0;
            res <= 0;
            iter <= 0;
            root <= 0;
            busy <= 0;
            done <= 0;
            trial <= 0;
        end else begin
            done <= 0;

            if (!busy) begin
                if (start) begin
                    x <= radicand;
                    rem <= 0;
                    res <= 0;
                    iter <= 16;
                    busy <= 1;
                end
            end else begin
                rem = {rem[29:0], x[31:30]};
                x = {x[29:0], 2'b00};
                trial = {res, 2'b01};
                if ({2'b00, rem} >= trial) begin
                    rem = rem - trial[31:0];
                    res = {res[14:0], 1'b1};
                end else begin
                    res = {res[14:0], 1'b0};
                end
                iter <= iter - 1;
                if (iter == 1) begin
                    root <= res;
                    busy <= 0;
                    done <= 1;
                end
            end
        end
    end
endmodule
