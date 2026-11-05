(* Filling: add 1 unit per PLC scan; the effective rate depends on the scan period *)
IF pump_output THEN
    level := level + 1;
END_IF;

IF level < setpoint THEN
    pump_output := TRUE;
ELSIF level >= (setpoint + 10) THEN
    pump_output := FALSE;
END_IF;

IF level > 100 THEN
    level := 100;   (* overflow limit *)
END_IF;