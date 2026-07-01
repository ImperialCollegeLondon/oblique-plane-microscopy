# Stage-triggered scanning

This folder is for the newer approach where the PIMag stage/controller generates camera triggers as it moves. Instead of NIS-Elements stepping an analog voltage and waiting empirically, the C-413 is configured to emit digital trigger pulses at defined physical distance intervals.

This is useful for scans such as:

> Move the PIMag/refocus axis by 100 µm and trigger the camera every 1 µm.

## Principle

The C-413 digital output can be configured in **Position Distance** trigger mode:

```text
CTO <TrigOutID> 2 <AxisID>      // select axis
CTO <TrigOutID> 3 0             // trigger mode 0 = PositionDistance
CTO <TrigOutID> 1 <TriggerStep> // distance between trigger pulses
TRO <TrigOutID> 1               // enable trigger output
```

Optional start/stop thresholds can restrict triggering to a scan window:

```text
CTO <TrigOutID> 8 <StartPosition>
CTO <TrigOutID> 9 <StopPosition>
```

The stage is then moved using a PI motion command such as `MOV` or `MVR`, and the controller emits pulses as the axis covers each trigger-step distance.

## Example: trigger every 1 µm over a 100 µm positive scan

Check the active units on your controller before using this. On the dOPM Micro-Manager helper code, trigger distances and trigger ranges are handled in **mm**.

For a 1 µm trigger step:

```text
// 1 µm = 0.001 mm
CTO 1 2 1
CTO 1 3 0
CTO 1 1 0.001
CTO 1 7 1
TRO 1 1
```

For a positive scan from 0.200 mm to 0.300 mm:

```text
CTO 1 8 0.200
CTO 1 9 0.300
TRO 1 1
MOV 1 0.300
```

The camera should be set to external trigger mode before the move starts.

## Safer run order

1. Disable trigger output: `TRO 1 0`.
2. Force/check the digital output low if needed.
3. Configure trigger axis, trigger mode, trigger step, polarity, and optional start/stop thresholds.
4. Arm the camera for external triggering.
5. Enable trigger output: `TRO 1 1`.
6. Start the PIMag move with `MOV` or `MVR`.
7. Disable trigger output after the scan.

## Relationship to the Micro-Manager helper code

The historical Java helper wraps these same concepts:

- `setupPITriggering(...)` disables triggering, sets the digital output low, selects axis 1, and selects trigger mode 0.
- `setPITriggerDistance(...)` writes `CTO <TrigOutID> 1 <distance>`.
- `setPITriggerRange(...)` writes `CTO <TrigOutID> 8 <lower>` and `CTO <TrigOutID> 9 <upper>`.
- `setPITriggerEnable(...)` writes `TRO <TrigOutID> <0/1>`.

## Notes

- The C-413 trigger settings are volatile; reconfigure after power cycling.
- Keep NIS analog-control mode, PI motion-command mode, and wavetable mode conceptually separate.
- Confirm trigger polarity with the camera input before relying on a scan.
