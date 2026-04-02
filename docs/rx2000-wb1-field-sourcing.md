# RX2000 WB1 Field Sourcing

This note answers one practical question:

- Which `WB1` values can come from `DXF` geometry?
- Which values must stay template-driven for the machine?

It complements [rx2000-wb1-j-record-map.md](rx2000-wb1-j-record-map.md) by focusing on
**data origin**, not just field naming.

## Short Answer

For the current `06_wire` flow, `DXF` can reliably provide:

- Each wire's two bond points: `bond_x`, `bond_y`
- Wire endpoint role: `role_code`
- Internal production order used to emit records in machine sequence
- Potential future geometric grouping: `group_no`
- Potential future angle-derived values such as `bond_angle`
- `bond_z` only if the source workflow eventually carries real Z values

Everything else in the RX2000 `J` record should still be treated as:

- recipe defaults
- role-specific defaults
- calibration values
- or machine-level parameters from `PFILE`

## Translation Pipeline

Current translation path:

1. `DXF 06_wire` entities are converted into structured wire geometry.
2. Geometry is ordered into one production sequence.
3. Only geometry-backed fields are written dynamically.
4. All other `WB1` words come from the selected template.

Relevant code:

- `core/export/wire_extraction.py`
- `core/export/wire_ordering.py`
- `core/export/wb1_writer.py`
- `core/export/wb1_field_sources.py`

## What DXF Gives Us

Current `06_wire` extraction can already produce:

- `wire_id`
- first point `x/y`
- second point `x/y`
- route polyline points
- wire length
- wire angle
- deterministic production order

That means the current geometry layer is strong on:

- coordinates
- point roles
- ordering
- geometric analysis

It is not strong on:

- machine calibration
- process tuning
- force / ultrasonic / timing recipe values
- camera coordinates
- device routing metadata

## J Record Source Matrix

Legend:

- `direct`: comes straight from geometry
- `derived`: can be computed from geometry or ordering logic
- `3d_only`: only available if the source carries true Z data
- `no`: not realistically available from raw `DXF 06_wire`

| Index | Field | DXF Availability | Current Source | Current DXF-backed | Notes |
| --- | --- | --- | --- | --- | --- |
| 0 | `role_code` | `derived` | wire endpoint role | Yes | Based on first/second point role in the extracted wire. |
| 1 | `cip_no` | `no` | shared template default | No | Product routing code, not geometric. |
| 2 | `loop_setting` | `no` | role template default | No | Process recipe value. |
| 3 | `z_down_percent` | `no` | shared template default | No | Machine motion tuning. |
| 4 | `angle_mode` | `no` | shared template default | No | Mode switch, not a raw coordinate. |
| 5 | `device_no` | `no` | shared template default | No | Product/device identifier. |
| 6 | `us_linear_time` | `no` | shared template default | No | Ultrasonic timing recipe. |
| 7 | `down_force_delay` | `no` | shared template default | No | Machine timing recipe. |
| 8 | `down_force_linear_time` | `no` | shared template default | No | Machine timing recipe. |
| 9 | `us_power_p` | `no` | role template default | No | Primary ultrasonic power. |
| 10 | `us_power_l` | `no` | shared template default | No | Secondary ultrasonic power. |
| 11 | `us_time_p` | `no` | role template default | No | Primary ultrasonic time. |
| 12 | `theta_input_correction` | `no` | shared template default | No | Calibration/correction field. |
| 13 | `search_speed` | `no` | role template default | No | Search motion recipe value. |
| 14 | `tool_set_distance` | `no` | role template default | No | Tool/process setup value. |
| 15 | `cut_force` | `no` | shared template default | No | Cutting recipe value. |
| 16 | `pull_distance` | `no` | role template default | No | Pull recipe value. |
| 17 | `start_relative_position` | `no` | role template default | No | Machine relative offset. |
| 18 | `loop_accel` | `no` | shared template default | No | Loop motion tuning. |
| 19 | `group_no` | `derived` | clustered ordering / fixed fallback | Yes | Current RX2000 default template derives group numbers from spatial wire clusters, while fixed mode is still available for custom templates. |
| 20 | `rotation_height` | `no` | shared template default | No | Machine motion recipe value. |
| 21 | `guide_distance` | `no` | shared template default | No | Tooling distance. |
| 22 | `pull_force` | `no` | role template default | No | Pull recipe value. |
| 23 | `search_distance` | `no` | role template default | No | Search recipe value. |
| 24 | `pull_height` | `no` | role template default | No | Pull recipe value. |
| 25 | `pushout_xy` | `no` | shared template default | No | Calibration value. |
| 26 | `pushout_z` | `no` | shared template default | No | Calibration value. |
| 27 | `pre_rotate_xy` | `no` | shared template default | No | Calibration value. |
| 28 | `rise_distance_15deg` | `no` | role template default | No | Recipe value. |
| 29 | `angle_correction` | `no` | shared template default | No | Correction field, not raw geometry. |
| 30 | `wait_time` | `no` | shared template default | No | Machine timing recipe. |
| 31 | `cut_speed` | `no` | shared template default | No | Cutting recipe value. |
| 32 | `camera_x` | `no` | hardcoded zero / future transform | No | Needs camera-to-bond calibration. |
| 33 | `al_wire_press_height` | `no` | role template default | No | Machine motion recipe. |
| 34 | `camera_y` | `no` | hardcoded zero / future transform | No | Needs camera-to-bond calibration. |
| 35 | `al_wire_press_distance` | `no` | shared template default | No | Machine motion recipe. |
| 36 | `camera_z` | `no` | hardcoded zero / future transform | No | Needs camera-to-bond calibration. |
| 37 | `zup_force` | `no` | shared template default | No | Machine force recipe. |
| 38 | `bond_x` | `direct` | wire geometry first/second point | Yes | Direct endpoint X after scaling. |
| 39 | `touch_correction` | `no` | shared template default | No | Calibration field. |
| 40 | `bond_y` | `direct` | wire geometry first/second point | Yes | Direct endpoint Y after scaling. |
| 41 | `reserved_ap` | `no` | shared template default | No | Reserved/unknown; keep template-controlled. |
| 42 | `bond_z` | `3d_only` | default Z fallback | No | Only geometry-backed if the source workflow carries real Z. |
| 43 | `reserved_ar` | `no` | shared template default | No | Reserved/unknown; keep template-controlled. |
| 44 | `contact_surface_position` | `no` | role template default | No | Process-specific contact setting. |
| 45 | `bond_angle` | `derived` | shared template default / optional wire_vector mode | No | The exporter can optionally write the wire vector angle, but RX2000 default templates still keep bond angle template-driven until machine validation confirms the heuristic. |
| 46 | `climb_angle` | `no` | shared template default | No | Machine motion recipe value. |
| 47 | `start_pressure` | `no` | shared template default | No | Bond force recipe value. |
| 48 | `end_pressure` | `no` | shared template default | No | Bond force recipe value. |
| 49 | `us_time_l` | `no` | shared template default | No | Secondary ultrasonic time. |
| 50 | `search_load` | `no` | shared template default | No | Search/load recipe value. |
| 51 | `descent_amount` | `no` | shared template default | No | Descent recipe value. |
| 52 | `pull_angle` | `no` | shared template default | No | Machine pull angle currently stays template-driven. |
| 53 | `cut_correction` | `no` | shared template default | No | Machine correction field. |
| 54 | `loop_correction` | `no` | shared template default | No | Machine correction field. |

## Practical Product Rule

If a field affects **where to bond**, it is a good candidate for geometry-driven generation.

If a field affects **how to bond**, it should stay in the recipe template unless we have
strong machine-side evidence that it can be derived safely.

That means the safest near-term `WB1` generation strategy is:

- geometry drives `bond_x`, `bond_y`, role/order, and later grouping/angle
- templates drive ultrasonic, force, timing, camera, correction, and `PFILE`

## Immediate Next Targets

The next geometry-backed upgrades with the best payoff are:

1. derive `bond_angle` from the wire endpoint vector
2. carry real `bond_z` when the source workflow can provide it
3. refine geometric clustering when more package layouts are available

Until those are in place, template defaults remain the correct source for those fields.
