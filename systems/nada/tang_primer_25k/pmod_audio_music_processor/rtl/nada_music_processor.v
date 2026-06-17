module nada_music_processor (
    input wire clk,
    input wire button_patch_previous,
    input wire button_patch_next,
    input wire button_song_next,
    input wire button_play_stop,

    output reg note_on_0 = 1'b0,
    output reg note_off_0 = 1'b0,
    output reg [7:0] note_0 = 8'd60,
    output reg [7:0] velocity_0 = 8'd100,
    output reg [2:0] patch_0 = 3'd0,

    output reg note_on_1 = 1'b0,
    output reg note_off_1 = 1'b0,
    output reg [7:0] note_1 = 8'd64,
    output reg [7:0] velocity_1 = 8'd100,
    output reg [2:0] patch_1 = 3'd0,

    output reg note_on_2 = 1'b0,
    output reg note_off_2 = 1'b0,
    output reg [7:0] note_2 = 8'd67,
    output reg [7:0] velocity_2 = 8'd100,
    output reg [2:0] patch_2 = 3'd0,

    output reg note_on_3 = 1'b0,
    output reg note_off_3 = 1'b0,
    output reg [7:0] note_3 = 8'd72,
    output reg [7:0] velocity_3 = 8'd100,
    output reg [2:0] patch_3 = 3'd0,

    output reg [2:0] selected_patch = 3'd0,
    output reg [1:0] selected_song = 2'd0,
    output reg running = 1'b0
);

localparam [3:0] OP_PATCH = 4'h1;
localparam [3:0] OP_NOTE_ON = 4'h2;
localparam [3:0] OP_NOTE_OFF = 4'h3;
localparam [3:0] OP_WAIT = 4'h4;
localparam [3:0] OP_JUMP = 4'h5;
localparam [3:0] OP_TEMPO = 4'h6;
localparam [3:0] OP_END = 4'hf;

reg [7:0] program_counter = 8'd0;
reg [15:0] wait_counter = 16'd0;
reg [16:0] tempo_counter = 17'd0;
reg [16:0] tempo_divisor = 17'd43750;

wire [31:0] instruction;
wire [3:0] opcode = instruction[31:28];
wire [3:0] voice = instruction[27:24];
wire tempo_tick = tempo_counter == tempo_divisor - 1'b1;

nada_music_program_rom program_rom (
    .song(selected_song),
    .address(program_counter),
    .instruction(instruction)
);

function [16:0] tempo_divisor_for;
    input [7:0] tempo_id;
    begin
        case (tempo_id[1:0])
            2'd0: tempo_divisor_for = 17'd65625;
            2'd1: tempo_divisor_for = 17'd52500;
            2'd2: tempo_divisor_for = 17'd43750;
            2'd3: tempo_divisor_for = 17'd37500;
            default: tempo_divisor_for = 17'd43750;
        endcase
    end
endfunction

always @(posedge clk) begin
    note_on_0 <= 1'b0;
    note_off_0 <= 1'b0;
    note_on_1 <= 1'b0;
    note_off_1 <= 1'b0;
    note_on_2 <= 1'b0;
    note_off_2 <= 1'b0;
    note_on_3 <= 1'b0;
    note_off_3 <= 1'b0;

    if (tempo_tick) begin
        tempo_counter <= 17'd0;
    end else begin
        tempo_counter <= tempo_counter + 1'b1;
    end

    if (button_patch_previous) begin
        selected_patch <= selected_patch - 1'b1;
        patch_0 <= selected_patch - 1'b1;
        patch_1 <= selected_patch - 1'b1;
        patch_2 <= selected_patch - 1'b1;
        patch_3 <= selected_patch - 1'b1;
        running <= 1'b1;
        program_counter <= 8'd0;
        wait_counter <= 16'd0;
        tempo_counter <= 17'd0;
        note_off_0 <= 1'b1;
        note_off_1 <= 1'b1;
        note_off_2 <= 1'b1;
        note_off_3 <= 1'b1;
    end else if (button_patch_next) begin
        selected_patch <= selected_patch + 1'b1;
        patch_0 <= selected_patch + 1'b1;
        patch_1 <= selected_patch + 1'b1;
        patch_2 <= selected_patch + 1'b1;
        patch_3 <= selected_patch + 1'b1;
        running <= 1'b1;
        program_counter <= 8'd0;
        wait_counter <= 16'd0;
        tempo_counter <= 17'd0;
        note_off_0 <= 1'b1;
        note_off_1 <= 1'b1;
        note_off_2 <= 1'b1;
        note_off_3 <= 1'b1;
    end else if (button_song_next) begin
        selected_song <= selected_song + 1'b1;
        patch_0 <= selected_patch;
        patch_1 <= selected_patch;
        patch_2 <= selected_patch;
        patch_3 <= selected_patch;
        running <= 1'b1;
        program_counter <= 8'd0;
        wait_counter <= 16'd0;
        tempo_counter <= 17'd0;
        note_off_0 <= 1'b1;
        note_off_1 <= 1'b1;
        note_off_2 <= 1'b1;
        note_off_3 <= 1'b1;
    end else if (button_play_stop) begin
        if (running) begin
            running <= 1'b0;
            wait_counter <= 16'd0;
            note_off_0 <= 1'b1;
            note_off_1 <= 1'b1;
            note_off_2 <= 1'b1;
            note_off_3 <= 1'b1;
        end else begin
            running <= 1'b1;
            program_counter <= 8'd0;
            wait_counter <= 16'd0;
            tempo_counter <= 17'd0;
            patch_0 <= selected_patch;
            patch_1 <= selected_patch;
            patch_2 <= selected_patch;
            patch_3 <= selected_patch;
        end
    end else if (running) begin
        if (wait_counter != 16'd0) begin
            if (tempo_tick) begin
                wait_counter <= wait_counter - 1'b1;
            end
        end else begin
            case (opcode)
                OP_PATCH: begin
                    case (voice)
                        4'd0: patch_0 <= instruction[2:0];
                        4'd1: patch_1 <= instruction[2:0];
                        4'd2: patch_2 <= instruction[2:0];
                        4'd3: patch_3 <= instruction[2:0];
                        default: patch_0 <= patch_0;
                    endcase
                    program_counter <= program_counter + 1'b1;
                end

                OP_NOTE_ON: begin
                    case (voice)
                        4'd0: begin
                            note_0 <= instruction[23:16];
                            velocity_0 <= instruction[15:8];
                            note_on_0 <= 1'b1;
                        end
                        4'd1: begin
                            note_1 <= instruction[23:16];
                            velocity_1 <= instruction[15:8];
                            note_on_1 <= 1'b1;
                        end
                        4'd2: begin
                            note_2 <= instruction[23:16];
                            velocity_2 <= instruction[15:8];
                            note_on_2 <= 1'b1;
                        end
                        4'd3: begin
                            note_3 <= instruction[23:16];
                            velocity_3 <= instruction[15:8];
                            note_on_3 <= 1'b1;
                        end
                        default: note_on_0 <= 1'b0;
                    endcase
                    program_counter <= program_counter + 1'b1;
                end

                OP_NOTE_OFF: begin
                    case (voice)
                        4'd0: note_off_0 <= 1'b1;
                        4'd1: note_off_1 <= 1'b1;
                        4'd2: note_off_2 <= 1'b1;
                        4'd3: note_off_3 <= 1'b1;
                        default: note_off_0 <= 1'b0;
                    endcase
                    program_counter <= program_counter + 1'b1;
                end

                OP_WAIT: begin
                    wait_counter <= instruction[15:0];
                    program_counter <= program_counter + 1'b1;
                end

                OP_JUMP: begin
                    program_counter <= instruction[7:0];
                end

                OP_TEMPO: begin
                    tempo_divisor <= tempo_divisor_for(instruction[7:0]);
                    tempo_counter <= 17'd0;
                    program_counter <= program_counter + 1'b1;
                end

                OP_END: begin
                    running <= 1'b0;
                    note_off_0 <= 1'b1;
                    note_off_1 <= 1'b1;
                    note_off_2 <= 1'b1;
                    note_off_3 <= 1'b1;
                end

                default: begin
                    program_counter <= program_counter + 1'b1;
                end
            endcase
        end
    end
end

endmodule
