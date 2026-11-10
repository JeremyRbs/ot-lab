(* (Session 7) *)
IF setpoint > 100 THEN
    setpoint := 100;
ELSIF setpoint < 0 THEN
    setpoint := 0;
END_IF;