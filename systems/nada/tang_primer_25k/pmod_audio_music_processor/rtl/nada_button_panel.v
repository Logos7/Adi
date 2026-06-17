module nada_button_panel (
    input wire clk,
    input wire button_0_n,
    input wire button_1_n,
    input wire button_2_n,
    input wire button_3_n,
    output reg button_0_pressed = 1'b0,
    output reg button_1_pressed = 1'b0,
    output reg button_2_pressed = 1'b0,
    output reg button_3_pressed = 1'b0
);

reg [1:0] button_0_sync = 2'b11;
reg [1:0] button_1_sync = 2'b11;
reg [1:0] button_2_sync = 2'b11;
reg [1:0] button_3_sync = 2'b11;

reg button_0_stable = 1'b1;
reg button_1_stable = 1'b1;
reg button_2_stable = 1'b1;
reg button_3_stable = 1'b1;

reg [14:0] button_0_debounce = 15'd0;
reg [14:0] button_1_debounce = 15'd0;
reg [14:0] button_2_debounce = 15'd0;
reg [14:0] button_3_debounce = 15'd0;

always @(posedge clk) begin
    button_0_pressed <= 1'b0;
    button_1_pressed <= 1'b0;
    button_2_pressed <= 1'b0;
    button_3_pressed <= 1'b0;

    button_0_sync <= {button_0_sync[0], button_0_n};
    button_1_sync <= {button_1_sync[0], button_1_n};
    button_2_sync <= {button_2_sync[0], button_2_n};
    button_3_sync <= {button_3_sync[0], button_3_n};

    if (button_0_sync[1] == button_0_stable) begin
        button_0_debounce <= 15'd0;
    end else if (&button_0_debounce) begin
        button_0_stable <= button_0_sync[1];
        button_0_debounce <= 15'd0;
        if (button_0_sync[1] == 1'b0) begin
            button_0_pressed <= 1'b1;
        end
    end else begin
        button_0_debounce <= button_0_debounce + 1'b1;
    end

    if (button_1_sync[1] == button_1_stable) begin
        button_1_debounce <= 15'd0;
    end else if (&button_1_debounce) begin
        button_1_stable <= button_1_sync[1];
        button_1_debounce <= 15'd0;
        if (button_1_sync[1] == 1'b0) begin
            button_1_pressed <= 1'b1;
        end
    end else begin
        button_1_debounce <= button_1_debounce + 1'b1;
    end

    if (button_2_sync[1] == button_2_stable) begin
        button_2_debounce <= 15'd0;
    end else if (&button_2_debounce) begin
        button_2_stable <= button_2_sync[1];
        button_2_debounce <= 15'd0;
        if (button_2_sync[1] == 1'b0) begin
            button_2_pressed <= 1'b1;
        end
    end else begin
        button_2_debounce <= button_2_debounce + 1'b1;
    end

    if (button_3_sync[1] == button_3_stable) begin
        button_3_debounce <= 15'd0;
    end else if (&button_3_debounce) begin
        button_3_stable <= button_3_sync[1];
        button_3_debounce <= 15'd0;
        if (button_3_sync[1] == 1'b0) begin
            button_3_pressed <= 1'b1;
        end
    end else begin
        button_3_debounce <= button_3_debounce + 1'b1;
    end
end

endmodule
