# Data Structure Rule

This README describes the rule for converting a circuit into a `node`-based data structure.

## Basic Format

Each circuit module is represented as a `node` data structure and contains five main fields. 

| Field | Meaning |
|---|---|
| `type` | Object type, e.g. `module`, `wire`, `and`, `multiplexer`, `invert` |
| `name` | Node name |
| `in` | Input signals of the node |
| `out` | Output signals of the node |
| `op` | Internal operations, including logic gates, nested components or submodules |

If the node `type` is not `module`, the `op` field can be omitted.

If the node `type` is `wire`,`bool` or `selector`, the `name` field can be omitted.

## Node names
Each node should have a unique name.

If the node name is not explicitly defined in the circuit, use the following naming rule:

```text
object type acronym + number label
```
For example:

```text
Mux1
And1
Or1
Mod1
Inv1
```

## Names

Every component, including nodes and I/O signals, should be assigned to the smallest containing `module`.

Each component should have a unique `ComponentName` within its containing module. If the component already has a name in the circuit SVG file, use that name directly.

If a component does not have a name in the circuit SVG file, use a temporary label such as `__1`, `__2`, etc.

Inside the assigned module, use local names only.

```text
a
out
__1
```

When the component is referenced from outside the assigned module, add the module scope as a prefix.

```text
ModuleName.ComponentName
```

For recursive module composition, scopes can be added repeatedly from outside to inside.

```text
a
Mod1.a
Mod2.Mod1.a
Top.Mod2.Mod1.a
```

## Signal Width

If a signal has more than one bit, use the `bit` field to describe its bit width.

For a 1-bit signal, the signal can be written as a string:

```yaml
in: [Mod1.clk, Mod1.rst]
```

For a multi-bit signal, write the signal as an object with `name` and `bit`:

```yaml
in:
  - name: Mod1.data
    bit: 100
```

## Operation Rule

Each operation is listed under `op`.

An operation may represent a logic gate, such as `and` or `or`, a nested component, such as a `multiplexer`, or a nested submodule.

### Multiplexer Rule

A multiplexer is written as a nested component, which contains 2 types of `op` : `bool` and `selector`.

- `bool` maps each data input to a selector value.
- `selector` defines the control signal of the multiplexer.
- The selected input is assigned to the multiplexer output.
