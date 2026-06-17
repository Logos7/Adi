module nada_music_program_rom (
    input wire [1:0] song,
    input wire [7:0] address,
    output reg [31:0] instruction
);

localparam [3:0] OP_PATCH = 4'h1;
localparam [3:0] OP_NOTE_ON = 4'h2;
localparam [3:0] OP_NOTE_OFF = 4'h3;
localparam [3:0] OP_WAIT = 4'h4;
localparam [3:0] OP_JUMP = 4'h5;
localparam [3:0] OP_TEMPO = 4'h6;
localparam [3:0] OP_END = 4'hf;

always @* begin
    instruction = {OP_END, 28'd0};

    case (song)
        2'd0: begin
            case (address)
                8'd0: instruction = {OP_TEMPO, 20'd0, 8'd2};
                8'd1: instruction = {OP_NOTE_ON, 4'd0, 8'd60, 8'd110, 8'd0};
                8'd2: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd3: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd4: instruction = {OP_NOTE_ON, 4'd0, 8'd64, 8'd110, 8'd0};
                8'd5: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd6: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd7: instruction = {OP_NOTE_ON, 4'd0, 8'd67, 8'd110, 8'd0};
                8'd8: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd9: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd10: instruction = {OP_NOTE_ON, 4'd0, 8'd72, 8'd118, 8'd0};
                8'd11: instruction = {OP_WAIT, 12'd0, 16'd12};
                8'd12: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd13: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd14: instruction = {OP_JUMP, 12'd0, 16'd1};
                default: instruction = {OP_END, 28'd0};
            endcase
        end

        2'd1: begin
            case (address)
                8'd0: instruction = {OP_TEMPO, 20'd0, 8'd3};
                8'd1: instruction = {OP_NOTE_ON, 4'd0, 8'd48, 8'd125, 8'd0};
                8'd2: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd3: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd4: instruction = {OP_WAIT, 12'd0, 16'd2};
                8'd5: instruction = {OP_NOTE_ON, 4'd0, 8'd48, 8'd118, 8'd0};
                8'd6: instruction = {OP_WAIT, 12'd0, 16'd4};
                8'd7: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd8: instruction = {OP_WAIT, 12'd0, 16'd2};
                8'd9: instruction = {OP_NOTE_ON, 4'd0, 8'd55, 8'd122, 8'd0};
                8'd10: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd11: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd12: instruction = {OP_WAIT, 12'd0, 16'd2};
                8'd13: instruction = {OP_NOTE_ON, 4'd0, 8'd58, 8'd118, 8'd0};
                8'd14: instruction = {OP_WAIT, 12'd0, 16'd4};
                8'd15: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd16: instruction = {OP_WAIT, 12'd0, 16'd2};
                8'd17: instruction = {OP_NOTE_ON, 4'd0, 8'd60, 8'd127, 8'd0};
                8'd18: instruction = {OP_WAIT, 12'd0, 16'd8};
                8'd19: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd20: instruction = {OP_WAIT, 12'd0, 16'd4};
                8'd21: instruction = {OP_JUMP, 12'd0, 16'd1};
                default: instruction = {OP_END, 28'd0};
            endcase
        end

        2'd2: begin
            case (address)
                8'd0: instruction = {OP_TEMPO, 20'd0, 8'd1};

                8'd1: instruction = {OP_NOTE_ON, 4'd0, 8'd60, 8'd102, 8'd0};
                8'd2: instruction = {OP_NOTE_ON, 4'd1, 8'd64, 8'd96, 8'd0};
                8'd3: instruction = {OP_NOTE_ON, 4'd2, 8'd67, 8'd96, 8'd0};
                8'd4: instruction = {OP_NOTE_ON, 4'd3, 8'd72, 8'd92, 8'd0};
                8'd5: instruction = {OP_WAIT, 12'd0, 16'd24};
                8'd6: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd7: instruction = {OP_NOTE_OFF, 4'd1, 24'd0};
                8'd8: instruction = {OP_NOTE_OFF, 4'd2, 24'd0};
                8'd9: instruction = {OP_NOTE_OFF, 4'd3, 24'd0};

                8'd10: instruction = {OP_NOTE_ON, 4'd0, 8'd57, 8'd102, 8'd0};
                8'd11: instruction = {OP_NOTE_ON, 4'd1, 8'd60, 8'd96, 8'd0};
                8'd12: instruction = {OP_NOTE_ON, 4'd2, 8'd64, 8'd96, 8'd0};
                8'd13: instruction = {OP_NOTE_ON, 4'd3, 8'd69, 8'd92, 8'd0};
                8'd14: instruction = {OP_WAIT, 12'd0, 16'd24};
                8'd15: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd16: instruction = {OP_NOTE_OFF, 4'd1, 24'd0};
                8'd17: instruction = {OP_NOTE_OFF, 4'd2, 24'd0};
                8'd18: instruction = {OP_NOTE_OFF, 4'd3, 24'd0};

                8'd19: instruction = {OP_NOTE_ON, 4'd0, 8'd53, 8'd102, 8'd0};
                8'd20: instruction = {OP_NOTE_ON, 4'd1, 8'd57, 8'd96, 8'd0};
                8'd21: instruction = {OP_NOTE_ON, 4'd2, 8'd60, 8'd96, 8'd0};
                8'd22: instruction = {OP_NOTE_ON, 4'd3, 8'd65, 8'd92, 8'd0};
                8'd23: instruction = {OP_WAIT, 12'd0, 16'd24};
                8'd24: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd25: instruction = {OP_NOTE_OFF, 4'd1, 24'd0};
                8'd26: instruction = {OP_NOTE_OFF, 4'd2, 24'd0};
                8'd27: instruction = {OP_NOTE_OFF, 4'd3, 24'd0};

                8'd28: instruction = {OP_NOTE_ON, 4'd0, 8'd55, 8'd102, 8'd0};
                8'd29: instruction = {OP_NOTE_ON, 4'd1, 8'd59, 8'd96, 8'd0};
                8'd30: instruction = {OP_NOTE_ON, 4'd2, 8'd62, 8'd96, 8'd0};
                8'd31: instruction = {OP_NOTE_ON, 4'd3, 8'd67, 8'd92, 8'd0};
                8'd32: instruction = {OP_WAIT, 12'd0, 16'd24};
                8'd33: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd34: instruction = {OP_NOTE_OFF, 4'd1, 24'd0};
                8'd35: instruction = {OP_NOTE_OFF, 4'd2, 24'd0};
                8'd36: instruction = {OP_NOTE_OFF, 4'd3, 24'd0};
                8'd37: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd38: instruction = {OP_JUMP, 12'd0, 16'd1};
                default: instruction = {OP_END, 28'd0};
            endcase
        end

        2'd3: begin
            case (address)
                8'd0: instruction = {OP_TEMPO, 20'd0, 8'd2};
                8'd1: instruction = {OP_NOTE_ON, 4'd0, 8'd72, 8'd112, 8'd0};
                8'd2: instruction = {OP_WAIT, 12'd0, 16'd8};
                8'd3: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd4: instruction = {OP_NOTE_ON, 4'd0, 8'd71, 8'd108, 8'd0};
                8'd5: instruction = {OP_WAIT, 12'd0, 16'd8};
                8'd6: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd7: instruction = {OP_NOTE_ON, 4'd0, 8'd67, 8'd112, 8'd0};
                8'd8: instruction = {OP_WAIT, 12'd0, 16'd8};
                8'd9: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd10: instruction = {OP_NOTE_ON, 4'd0, 8'd64, 8'd108, 8'd0};
                8'd11: instruction = {OP_WAIT, 12'd0, 16'd8};
                8'd12: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd13: instruction = {OP_NOTE_ON, 4'd0, 8'd60, 8'd112, 8'd0};
                8'd14: instruction = {OP_NOTE_ON, 4'd1, 8'd64, 8'd96, 8'd0};
                8'd15: instruction = {OP_NOTE_ON, 4'd2, 8'd67, 8'd96, 8'd0};
                8'd16: instruction = {OP_WAIT, 12'd0, 16'd20};
                8'd17: instruction = {OP_NOTE_OFF, 4'd0, 24'd0};
                8'd18: instruction = {OP_NOTE_OFF, 4'd1, 24'd0};
                8'd19: instruction = {OP_NOTE_OFF, 4'd2, 24'd0};
                8'd20: instruction = {OP_WAIT, 12'd0, 16'd6};
                8'd21: instruction = {OP_JUMP, 12'd0, 16'd1};
                default: instruction = {OP_END, 28'd0};
            endcase
        end

        default: instruction = {OP_END, 28'd0};
    endcase
end

endmodule
