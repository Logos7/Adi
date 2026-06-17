module nada_sigma_delta_dac (
    input wire clk,
    input wire [9:0] sample,
    output wire audio_bit
);

reg [10:0] accumulator = 11'd0;

always @(posedge clk) begin
    accumulator <= {1'b0, accumulator[9:0]} + {1'b0, sample};
end

assign audio_bit = accumulator[10];

endmodule
