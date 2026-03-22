# Draw Assistant — Symbol Placer

Inkscape 1.x extension that embeds pre-drawn symbols from the AnalogHub symbol
libraries into your document at their original scale.

---

## Installation

1. Locate your Inkscape **user extensions folder**:
   | OS | Path |
   |----|------|
   | Windows | `%APPDATA%\inkscape\extensions\` |
   | Linux   | `~/.config/inkscape/extensions/` |
   | macOS   | `~/Library/Application Support/org.inkscape.Inkscape/config/inkscape/extensions/` |

2. Copy these two files into that folder:
   - `drawAssistant.py`
   - `drawAssistant.inx`

3. Restart Inkscape.

The extension appears under **Extensions › Draw Assistant › Place Symbol**.

> **Symbol library SVGs are downloaded automatically on first use** and cached in a
> `symbols/` sub-folder inside your extensions directory.  An internet connection
> is required only for the first use of each library.

---

## Usage

### Place a symbol by ID

1. *(Optional)* Select an object on the canvas — the symbol will be centred there.
2. Open **Extensions › Draw Assistant › Place Symbol**.
3. Choose the correct library from the dropdown.
4. Type the **exact Symbol ID** (case-sensitive) in the text field.
5. Click **Apply**.

### Replace a placeholder shape

1. Draw a rough placeholder shape where you want the symbol.
2. Open **Object › Object Properties** and set the **Label** to the Symbol ID
   (e.g. `Opamp`).
3. Select the shape.
4. Open the extension, choose the library, check **Replace selected shape**.
5. Click **Apply** — the placeholder is deleted and the symbol is placed at the
   same centre position.

---

## Symbol IDs

### Analog (`AH-analog`)
`DC_voltage_source`, `DC_current_source`, `Sinewave_voltage_source`,
`Pulse_voltage_source`, `Sawtooth_voltage_source`, `Step_voltage_source`,
`Triangle_voltage_source`, `PWM_voltage_source`, `FM_source`, `AM_source`, `PM_source`,
`Opamp`, `Differential_Opamp_1`, `Differential_Opamp_2`,
`Single_ended_Opamp_common_mode`, `Differential_Opamp_1_common_mode`,
`Differential_Opamp_2_common_mode`, `Comparator`, `Differential_comparator_1`,
`Differential_comparator_2`, `Comparator_with_hysteresys`,
`Differential_comparator_1_with_hysteresys`, `Differential_comparator_2_with_hysteresys`,
`Sample_and_Hold`, `N-bit_ADC`, `3-bit_ADC`, `4-bit_ADC`,
`N-bit_DAC`, `3-bit_DAC`, `4-bit_DAC`,
`MUX_2:1`, `MUX_3:1`, `MUX_4:1`, `MUX_N:1`,
`DEMUX_1:2`, `DEMUX_1:3`, `DEMUX_1:4`, `DEMUX_1:N`,
`Switch_open__a_`, `Switch_closed__a_`, `Switch_2__a_`,
`Switch_open__b_`, `Switch_closed__b_`, `Switch_2__b_`,
`Capacitor`, `Capacitor_polarised`, `Resistor_1`, `Resistor_2`,
`Inductor`, `Memristor`, `Diode`, `Photodiode`, `LED`,
`Zener_diode`, `Schottky_diode`, `Stabilitron`,
`NMOS`, `PMOS`, `NMOS_with_substrate`, `PMOS_with_substrate`,
`NMOS_with_shorted_substrate`, `PMOS_with_shorted_substrate`,
`NPN`, `PNP`,
`Power_pin`, `Input_pin`, `Output_pin`, `Inout_pin`,
`Circle_pin`, `Square_pin`, `Crossed_square_pin`, `Ground_pin`,
`Transformer_A`, `Transformer_B`, `Transformer_C`, `Transformer_D`, `Transformer_E`

### Behavioural (`AH-behavioural`)
`LPF`, `HPF`, `Bandpass_filter`, `Bandstop_filter`,
`FIR_filter_generic`, `FIR_LPF_generic`, `FIR_BPF_generic`, `FIR_HPF`,
`IIR_filter_generic`, `IIR_LPF_generic`, `IIR_BPF_generic`, `IIR_HPF_generic`,
`FIR_LPF`, `FIR_BPF`, `IIR_LPF`, `IIR_HPF`, `IIR_BPF`,
`Clock_source`, `Sine_source`, `PWM_source`, `Sawtooth_source`, `Step_source`,
`Voltage_reference`, `Current_reference`, `Crystal_oscillator`, `Bandgap_reference`,
`LDO`, `ADC_generic`, `DAC_generic`,
`MUX_2:1`, `MUX_3:1`, `MUX_4:1`, `MUX_1:N`,
`DEMUX_2:1`, `DEMUX_3:1`, `DEMUX_4:1`, `DEMUX_N:1`,
`Switch_open__a_`, `Switch_closed__a_`, `Switch2__a_`,
`Gain_1`, `Gain_2`, `Buffer`, `OTA_1`, `OTA_2`, `OTA_differential`,
`TIA_1`, `TIA_2`, `TIA_differential`, `EA_1`, `EA_2`, `EA_differential`,
`LNA_1`, `LNA_2`, `LNA_differential`, `Gm-stage_1`, `Gm-stage_2`, `Gm-stage_differential`,
`Comparator_1`, `Comparator_2`, `Comparator_3`,
`Comparator_with_hysteresis_1`, `Comparator_with_hysteresis_2`,
`Differential_comparator`, `Differential_comparator_with_hysteresis`,
`Integrator_1`, `Integrator_s-domain`, `Integrator_3`,
`Differentiator_s-domain`, `Differentiator_2`, `Differentiator_3`,
`Multiplication`, `Division`, `Delay`, `Delay_z-domain`,
`Summator_2`, `Summator_3`, `Summator_4`,
`Subtract_2`, `Subtract_3`, `Subtract_4`, `Subtract_round`,
`LVDS_1`, `LVDS_2`, `Driver_1`, `Driver_2`,
`VCO_1`, `VCO_2`, `Charge_pump`, `Mixer`,
`Phase_shifter_1`, `Phase_shifter_2`, `PLL`, `DLL`,
`Frequency_divider`, `Loop_filter`, `PFD`, `Phase_detector`,
`Digital_processing`, `Decoder`, `Counter`, `State_machine`, `Encoder`, `FSM`,
`Sensor_generic`, `ESD_generic`, `I2C`, `SPI`

### Logic Gates (`AH-logic-gates`)
`Inverter`, `Buffer`, `Schmitt_Trigger`, `Schmitt_Trigger_Inverted`,
`NAND2`, `NAND3`, `NAND4`,
`AND2`, `AND3`, `AND4`,
`OR2`, `OR3`, `OR4`,
`NOR2`, `NOR3`, `NOR4`,
`XOR2`, `XOR3`, `XOR4`,
`D-trigger`, `D-trigger_clocked_positive`, `D-trigger_clocked_negative`,
`RS-trigger_positive`, `RS-trigger_negative`,
`T-trigger`, `JK-trigger`
