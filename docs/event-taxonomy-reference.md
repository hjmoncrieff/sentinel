# Event Taxonomy Reference

_Generated from `config/taxonomy/event_types.json` on 2026-04-03._

This is the current SENTINEL event hierarchy:

- `Type`: broad analytical domain
- `Category`: event family within that domain
- `Subcategory`: narrower mechanism-level interpretation

The pipeline still keeps legacy internal family codes for compatibility, but this document is the public-facing structure reference.

## Type -> Category -> Subcategory

| Type | Category | Category Label | Default Subcategory | Construct Destinations | Analyst Lenses | Description |
| --- | --- | --- | --- | --- | --- | --- |
| `international` | `aid` | Military Aid | `external_security_support` | - `militarization`<br>- `security_fragmentation` | - `international`<br>- `military` | Foreign military assistance, financing, training, or equipment transfers. |
| `international` | `coop` | Security Cooperation | `external_security_alignment` | - `security_fragmentation`<br>- `militarization` | - `international`<br>- `security` | Joint security cooperation, operational partnerships, bilateral support, or coordination that does not fit exercise or aid cleanly. |
| `military` | `purge` | Purge / Command Reshuffle | `command_and_coercive_control` | - `militarization`<br>- `regime_vulnerability` | - `military`<br>- `political` | Forced removals, retirements, command restructuring, or politically salient officer turnover. |
| `military` | `procurement` | Procurement / Arms | `force_build_up_and_equipment` | - `militarization` | - `military`<br>- `international`<br>- `economist` | Weapons acquisitions, defense contracts, or arms transfer decisions. |
| `military` | `exercise` | Military Exercise | `force_posture_and_training` | - `militarization` | - `military`<br>- `international` | Bilateral or multilateral military training exercises or drills. |
| `political` | `coup` | Coup / Coup Plot | `irregular_transfer_and_command_break` | - `regime_vulnerability`<br>- `militarization` | - `political`<br>- `military` | Attempted, threatened, or actual seizure of political power involving military or security actors. |
| `political` | `protest` | Civil-Military Protest | `contention_and_state_response` | - `regime_vulnerability`<br>- `security_fragmentation` | - `political`<br>- `security` | Civil unrest or protest episodes that directly involve security forces, military institutions, or militarized policing. |
| `political` | `reform` | Security Sector Reform | `institutional_security_reordering` | - `regime_vulnerability`<br>- `militarization` | - `political`<br>- `military` | Legal, doctrinal, administrative, or institutional reforms affecting civil-military relations or security governance. |
| `political` | `peace` | Peace Process | `conflict_management_and_settlement` | - `security_fragmentation`<br>- `regime_vulnerability` | - `political`<br>- `security`<br>- `international` | Ceasefires, negotiations, DDR milestones, and peace implementation events. |
| `political` | `other` | Other | `other_institutional_relevance` | - `regime_vulnerability` | - `political` | Institutionally relevant events not captured by the controlled categories above. |
| `security` | `conflict` | Armed Conflict | `armed_fragmentation_and_territorial_control` | - `security_fragmentation`<br>- `regime_vulnerability` | - `security`<br>- `political` | Combat or violent confrontation involving state security forces and organized armed actors. |
| `security` | `oc` | Organized Crime / Transnational Security | `armed_non_state_and_illicit_order` | - `security_fragmentation`<br>- `regime_vulnerability` | - `security`<br>- `political`<br>- `economist` | Events involving organized crime, trafficking networks, illicit economies, or related military and security responses. |

## Types

### `international`

- categories: `2`
- categories included: `aid`, `coop`

### `military`

- categories: `3`
- categories included: `purge`, `procurement`, `exercise`

### `political`

- categories: `5`
- categories included: `coup`, `protest`, `reform`, `peace`, `other`

### `security`

- categories: `2`
- categories included: `conflict`, `oc`

## Category -> Subcategory Map

### `international`

- `aid`
  default: `external_security_support`
- `coop`
  default: `external_security_alignment`

### `military`

- `purge`
  default: `command_and_coercive_control`
- `procurement`
  default: `force_build_up_and_equipment`
- `exercise`
  default: `force_posture_and_training`

### `political`

- `coup`
  default: `irregular_transfer_and_command_break`
- `protest`
  default: `contention_and_state_response`
- `reform`
  default: `institutional_security_reordering`
- `peace`
  default: `conflict_management_and_settlement`
- `other`
  default: `other_institutional_relevance`

### `security`

- `conflict`
  default: `armed_fragmentation_and_territorial_control`
- `oc`
  default: `armed_non_state_and_illicit_order`

## Update Rule

Whenever `config/taxonomy/event_types.json` changes, regenerate this file with:

```bash
python3 scripts/analysis/update_event_taxonomy_reference.py
```
