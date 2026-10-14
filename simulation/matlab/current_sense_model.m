clear all; close all; clc;

%% Setup
fprintf('\n');
fprintf('╔══════════════════════════════════════╗\n');
fprintf('║   Motor Driver Current-Sense Model   ║\n');
fprintf('║   DRV8833 shunt + LM358 diff amp     ║\n');
fprintf('╚══════════════════════════════════════╝\n\n');

% Design parameters
% PLACEHOLDERS: the schematic labels these parts only as "R" / "R_Shunt".
% Replace with the real values before trusting any output.
R_shunt = 0.1;     % R1, R2 sense resistors (ohms)
R_in    = 10e3;    % Difference-amp input resistors (ohms)
R_f     = 100e3;   % Difference-amp feedback / reference resistors (ohms)
VCC     = 5.0;     % LM358 supply (V)

% Datasheet figures
ISEN_trip = 0.200; % V: DRV8833 starts current chopping at 200 mV on xISEN
headroom  = 1.5;   % V: LM358 output typically swings to about VCC - 1.5 V
V_OL      = 0.02;  % V: approximate output low level with a light load

gain   = R_f / R_in;
I_trip = ISEN_trip / R_shunt;
I_sat  = (VCC - headroom) / (gain * R_shunt);

fprintf('Parameters (placeholders until confirmed):\n');
fprintf('  Rshunt = %g Ω   Rin = %g Ω   Rf = %g Ω   VCC = %g V\n', R_shunt, R_in, R_f, VCC);
fprintf('  Amplifier gain:            %.2f V/V  (%.3f V/A)\n', gain, gain * R_shunt);
fprintf('  DRV8833 chopping current:  %.3f A  (200 mV / Rshunt)\n', I_trip);
fprintf('  LM358 saturation current:  %.3f A  (output reaches VCC - %.1f V)\n\n', I_sat, headroom);

% Get list of .dat files in workdir folder
dataFiles = dir('workdir/*.dat');

if isempty(dataFiles)
    fprintf('\033[91m✗ No data files found in workdir/ folder\033[0m\n');
    return;
end

fprintf('\033[92m✓ Found %d data file(s)\033[0m\n\n', length(dataFiles));

%% Process each data file
for fileIdx = 1:length(dataFiles)
    filename = fullfile(dataFiles(fileIdx).folder, dataFiles(fileIdx).name);
    fprintf('\033[94mProcessing:\033[0m %s\n', filename);

    try
        data = readmatrix(filename, 'FileType', 'text');
        current = data(:, 1);  % Column 1: motor current (Amps)

        [V_sense, V_ideal, V_out, P_shunt] = senseChain(current, R_shunt, gain, VCC, headroom, V_OL);

        fprintf('  %8s %12s %10s %12s  Notes\n', 'I (A)', 'Vsense (mV)', 'Vout (V)', 'Pshunt (mW)');
        for k = 1:length(current)
            notes = '';
            if current(k) >= I_trip
                notes = [notes 'DRV8833 chopping '];
            end
            if V_ideal(k) > V_out(k)
                notes = [notes 'op-amp saturated'];
            end
            fprintf('  %8.3f %12.1f %10.3f %12.1f  %s\n', current(k), V_sense(k) * 1e3, ...
                V_out(k), P_shunt(k) * 1e3, notes);
        end
        fprintf('\n');

        figure('Name', dataFiles(fileIdx).name);
        plot(current, V_out, 'o-', current, V_ideal, '--');
        xline(I_trip, ':', 'DRV8833 chop');
        xlabel('Motor current (A)'); ylabel('Sense amp output (V)');
        legend('LM358 output (clamped)', 'Ideal gain', 'Location', 'northwest');
        grid on;

    catch ME
        fprintf('\033[91m✗ Error processing file: %s\033[0m\n\n', ME.message);
        continue;
    end
end

fprintf('Done!\n\n');


%% ========== LOCAL FUNCTIONS (MUST BE AT VERY BOTTOM) ==========

function [V_sense, V_ideal, V_out, P_shunt] = senseChain(current, R_shunt, gain, VCC, headroom, V_OL)
    % Low-side shunt followed by a 4-resistor difference amplifier
    V_sense = current * R_shunt;
    V_ideal = gain * V_sense;
    V_out   = min(max(V_ideal, V_OL), VCC - headroom);
    P_shunt = current.^2 * R_shunt;
end
