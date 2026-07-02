# OWM DSL Syntax Reference

Renderer: https://onlinewardleymaps.com | VS Code Wardley Maps extension

## Core Elements

```
title [Map Title]
style wardley

// Anchors — user needs at top of map
anchor [Name] [visibility, maturity]

// Components
component [Name] [visibility, maturity]
component [Name] [visibility, maturity] inertia

// Dependencies
[Component A]->[Component B]
[Component A]+>[Component B]    // flow link (shows data/value flow)

// Evolution arrows
evolve [Component Name] [target_maturity]

// Pipelines (show a component spanning stages)
pipeline [Name] [start_maturity, end_maturity]

// Annotations
note [Text] [visibility, maturity]
annotation 1 [[v1,m1],[v2,m2]] Annotation text
```

## Coordinate System

```
[visibility, maturity]

Visibility (Y-axis, vertical):
  1.0 = directly user-facing (top)
  0.0 = invisible infrastructure (bottom)

Maturity (X-axis, horizontal):
  0.00–0.20 = Genesis
  0.20–0.40 = Custom Built
  0.40–0.70 = Product
  0.70–1.00 = Commodity
```

## Style Values

```
style wardley      // standard Wardley map
style lean         // lean canvas variant
```

## Links

```
A->B               // A depends on B (standard dependency)
A+>B               // A flows to/from B (data or value flow)
```

## Modifiers

```
inertia            // component resists evolution pressure
label [+x, +y]     // offset the component label (pixels)
```

## Annotation Format

```
annotation 1 [[0.43, 0.35]] Note text here
annotation 2 [[0.79, 0.61],[0.52, 0.52]] Spans two points
annotations
  1 This is annotation one
  2 This is annotation two
```

## Canonical Tea Shop Example

```
title Tea Shop
anchor Customer [0.97, 0.50]
component Cup of Tea [0.79, 0.61]
component Tea [0.63, 0.81]
component Hot Water [0.52, 0.52]
component Kettle [0.43, 0.35] inertia
component Water [0.38, 0.82]
component Power [0.10, 0.70]
Customer->Cup of Tea
Cup of Tea->Tea
Cup of Tea->Hot Water
Hot Water->Water
Hot Water->Kettle
Kettle->Power
evolve Kettle 0.62
```
