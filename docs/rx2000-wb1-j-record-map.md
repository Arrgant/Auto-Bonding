# RX2000 WB1 J-Record Map

This note tracks what we currently understand about the `J` segment in RX2000
`WB1` files. It is based on the real sample files below plus the existing
template writer implementation:

- `C:\Users\Arrgant\Documents\xwechat_files\wxid_bqjscsvibn0d22_5c06\msg\file\2026-04\13AL0208.WB1`
- `C:\Users\Arrgant\Documents\xwechat_files\wxid_bqjscsvibn0d22_5c06\msg\file\2026-04\RX2000 Setting RearCut 20251215.xlsm`
- [wire_recipe_defaults.py](C:/Users/Arrgant/Desktop/Auto-Bonding/core/export/wire_recipe_defaults.py)

## Scope

- `WB1` is a segmented text file, not a pure binary file.
- `PRE / G / H / I` are header-like segments.
- `J` is the repeated production record segment.
- One wire maps to two `J` records in the current RX2000 sample:
  - `role_code = 0` for the first bond
  - `role_code = 2` for the second bond
- The current implementation treats each `J` row as a fixed-width `55` word record.

## Status

- `Confirmed`: direct worksheet labels or formula references clearly identify the field.
- `Partial`: the field name is a good working name, but unit/range/behavior still needs machine-side confirmation.
- `Unknown`: placeholder or reserved field with no reliable business meaning yet.

## J Segment Field Map

| Index | Field | Status | Notes |
| --- | --- | --- | --- |
| 0 | `role_code` | Confirmed | `0` and `2` match first/second bond rows in the sample workbook. |
| 1 | `cip_no` | Confirmed | Directly labeled in the workbook. |
| 2 | `loop_setting` | Confirmed | Directly labeled in the workbook. |
| 3 | `z_down_percent` | Partial | Name and placement are stable, but exact machine semantics still need confirmation. |
| 4 | `angle_mode` | Partial | Matches the angle-related slot from the workbook conversion sheet. |
| 5 | `device_no` | Confirmed | Directly labeled in the workbook. |
| 6 | `us_linear_time` | Partial | Stable slot, but final unit meaning still needs confirmation. |
| 7 | `down_force_delay` | Partial | Stable slot, machine-side effect still to confirm. |
| 8 | `down_force_linear_time` | Partial | Stable slot, machine-side effect still to confirm. |
| 9 | `us_power_p` | Confirmed | Maps to the primary US power field in the workbook conversion. |
| 10 | `us_power_l` | Confirmed | Maps to the secondary US power field in the workbook conversion. |
| 11 | `us_time_p` | Confirmed | Maps to the primary US time field. |
| 12 | `theta_input_correction` | Partial | Theta-related correction slot, unit still to confirm. |
| 13 | `search_speed` | Confirmed | Directly labeled as search speed in the workbook conversion. |
| 14 | `tool_set_distance` | Confirmed | Directly labeled as tool-set distance. |
| 15 | `cut_force` | Confirmed | Directly labeled as cut force. |
| 16 | `pull_distance` | Confirmed | Directly labeled as pull distance. |
| 17 | `start_relative_position` | Partial | Stable slot, wording may still need adjustment. |
| 18 | `loop_accel` | Partial | Stable loop-related slot, unit still to confirm. |
| 19 | `group_no` | Confirmed | Directly labeled as `Group No.` |
| 20 | `rotation_height` | Partial | Stable rotation-height slot, unit still to confirm. |
| 21 | `guide_distance` | Confirmed | Directly labeled as guide distance. |
| 22 | `pull_force` | Confirmed | Directly labeled as pull force. |
| 23 | `search_distance` | Confirmed | Directly labeled as `s-distance`. |
| 24 | `pull_height` | Confirmed | Directly labeled as pull height. |
| 25 | `pushout_xy` | Partial | Stable slot, likely XY push-out correction. |
| 26 | `pushout_z` | Partial | Stable slot, likely Z push-out correction. |
| 27 | `pre_rotate_xy` | Partial | Stable slot, likely pre-rotate XY correction. |
| 28 | `rise_distance_15deg` | Partial | Stable slot, likely 15-degree rise amount. |
| 29 | `angle_correction` | Confirmed | Directly labeled as angle correction / background angle style field. |
| 30 | `wait_time` | Confirmed | Directly labeled as wait time. |
| 31 | `cut_speed` | Confirmed | Directly labeled as cut speed. |
| 32 | `camera_x` | Confirmed | Workbook conversion sheet maps this to camera X. |
| 33 | `al_wire_press_height` | Partial | Stable slot, exact machine phrasing still to confirm. |
| 34 | `camera_y` | Confirmed | Workbook conversion sheet maps this to camera Y. |
| 35 | `al_wire_press_distance` | Partial | Stable slot, exact machine phrasing still to confirm. |
| 36 | `camera_z` | Confirmed | Workbook conversion sheet maps this to camera Z. |
| 37 | `zup_force` | Partial | Stable slot, force naming still to confirm. |
| 38 | `bond_x` | Confirmed | Workbook conversion sheet maps this to bond X. |
| 39 | `touch_correction` | Confirmed | Directly labeled as touch correction / touch position style field. |
| 40 | `bond_y` | Confirmed | Workbook conversion sheet maps this to bond Y. |
| 41 | `reserved_ap` | Unknown | Placeholder slot with no reliable meaning yet. |
| 42 | `bond_z` | Confirmed | Workbook conversion sheet maps this to bond Z. |
| 43 | `reserved_ar` | Unknown | Placeholder slot with no reliable meaning yet. |
| 44 | `contact_surface_position` | Confirmed | Directly labeled as contact-surface position. |
| 45 | `bond_angle` | Confirmed | Directly labeled as bond angle. |
| 46 | `climb_angle` | Confirmed | Directly labeled as climb angle. |
| 47 | `start_pressure` | Partial | Stable pressure slot, exact machine wording still to confirm. |
| 48 | `end_pressure` | Partial | Stable pressure slot, exact machine wording still to confirm. |
| 49 | `us_time_l` | Confirmed | Maps to the secondary US time field. |
| 50 | `search_load` | Confirmed | Directly labeled as search load / search force style field. |
| 51 | `descent_amount` | Partial | Stable descent-related slot, unit still to confirm. |
| 52 | `pull_angle` | Confirmed | Directly labeled as pull angle. |
| 53 | `cut_correction` | Partial | Stable cut correction slot, exact behavior still to confirm. |
| 54 | `loop_correction` | Partial | Stable loop correction slot, exact behavior still to confirm. |

## Header Segment Notes

- `PRE`, `G`, `H`, and `I` are already template-addressable in code with keys like:
  - `PRE:1:2`
  - `G:1:4`
  - `H:0:5`
  - `I:0:12`
- We can override those words safely without reinterpreting the entire header.
- The current default header tokens come from the real `13AL0208.WB1` sample and are stored in:
  - [wire_recipe_defaults.py](C:/Users/Arrgant/Desktop/Auto-Bonding/core/export/wire_recipe_defaults.py)

## What Is Still Missing

- Camera-to-bond coordinate conversion is still not modeled.
- Some angle, pressure, correction, and push-out slots still need machine-side confirmation.
- `reserved_ap` and `reserved_ar` should remain template-controlled until we have stronger evidence.
- The file header is editable by word index, but we do not yet have a full business-name map for every header field.

## Practical Rule For Now

- Keep `Confirmed` fields writable from geometry or named template parameters.
- Keep `Partial` fields template-driven by default.
- Keep `Unknown` fields copied from the machine template unless production validation says otherwise.
