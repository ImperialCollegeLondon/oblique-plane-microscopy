# PIMag scanning and refocus control

This repository collects setup notes, PIMikroMove macros, and command examples for controlling a PI PIMag linear stage in a dOPM/OPM refocussing path.

The current hardware context is a PI **V-522 PIMag voice-coil linear stage** driven by a **C-413 PIMag motion controller**. The V-522 stage is used as a fast linear actuator for the refocussing/prism mirror assembly. The optical context for the microscope geometry is described in:

> Hugh Sparks, Lucas Dent, Chris Bakal, Axel Behrens, Guillaume Salbreux, and Chris Dunsby, **“Dual-view oblique plane microscopy (dOPM),”** *Biomedical Optics Express* **11**(12), 7204-7220 (2020).  
> https://opg.optica.org/boe/fulltext.cfm?uri=boe-11-12-7204

## Control modes covered here

There are several different ways to drive the PIMag/C-413 combination. They are useful for different acquisition modes and should not be mixed without checking which source currently owns the axis target.

| Folder | Purpose | Timing model |
|---|---|---|
| [`analog-control-for-nis-elements/`](analog-control-for-nis-elements/) | Configure the C-413 so NIS-Elements can drive the PIMag using an analog DAQ voltage. This is the historical NIS-Elements “Piezo Z” hack. | NIS-Elements writes voltages and waits empirically for settling before grabbing images, unless using NIS hardware-timed triggered piezo mode. |
| [`stage-triggered-scanning/`](stage-triggered-scanning/) | Use C-413 position-distance triggering. The stage moves under PI command control and emits TTL triggers every defined physical distance. | The stage/controller generates position-based hardware triggers during a commanded move. |
| [`wavetable-control/`](wavetable-control/) | Use the C-413 wave generator/wavetables for internally generated motion profiles. | The C-413 outputs waveform points synchronously with its servo cycle. |

## Physical PIMag travel to refocus scan range

The PIMag moves the refocussing/prism mirror assembly in physical space. The apparent axial refocus range in the oblique-view coordinate system is smaller than the PIMag travel because it depends on the prism/mirror tilt and the refractive-index ratio between air-side motion and aqueous sample space.

The working geometric model used here is:

```matlab
refocus_mirror = 2 * sin(prism * pi / 180) / n_ratio;
refocus_z_view = refocus_mirror * cos(prism * pi / 180);
nis_scan_range_about_zero = refocus_z_view * pimag_range / 2;
```

where:

- `prism` is the prism/mirror tilt angle in degrees.
- `pimag_range` is the full physical PIMag travel in µm.
- `n_ratio = 1.33` is used for the air-to-aqueous scaling.
- `refocus_z_view` is the dimensionless conversion from PIMag physical travel to the refocus/view-z coordinate.
- `nis_scan_range_about_zero` is the positive/negative NIS scan limit for a scan centred on zero.

For a 5 mm PIMag range (`pimag_range = 5000 µm`) and `n_ratio = 1.33`:

| Prism tilt | `refocus_mirror` | `refocus_z_view` | NIS range about zero | Full NIS span |
|---:|---:|---:|---:|---:|
| 17.5° | 0.452189 | 0.431260 | ±1078.15 µm | 2156.30 µm |
| 22.5° | 0.575464 | 0.531659 | ±1329.15 µm | 2658.30 µm |

The sign is a microscope-specific convention. In the historical NIS-Elements setup the 17.5° magnitude appears as `-10 V -> +1078 µm` and `+10 V -> -1078 µm`, so the NIS sign is reversed relative to a positive voltage convention.

## Practical notes

- Do not assume the C-413 is in the required mode after power cycling. Many settings are volatile unless explicitly saved to nonvolatile memory.
- For NIS analog-voltage control, initialise/reference/autozero the stage in PIMikroMove first, turn the servo on, then run the analog-control macro.
- For stage-triggered scanning, disable/clear the trigger output before arming the camera, configure `CTO`, then enable with `TRO` immediately before the scan.
- For wavetable scanning, remember that active wave generator output, analog control input, and normal `MOV`/`MVR` motion commands interact; only one target/control source should own the axis for a given acquisition mode.

## Repository status

This is an archival/control-notes repository for a specific microscope hardware configuration. Before using on another system, verify:

1. C-413 serial number and axis numbering.
2. Analog input/output wiring on the C-413 I/O connector.
3. NIS-Elements DAQ line mapping.
4. PIMag travel limits and sign convention.
5. Camera trigger polarity and timing.
