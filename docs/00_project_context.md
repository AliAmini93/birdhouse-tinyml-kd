# 00 - Project Context

## Deployment Goal

The project target is low-power acoustic bird detection for a Birdhouse monitoring node.

The deployed model should be binary:

```text
bird / non-bird
```

The final model should be small enough for embedded TinyML deployment on:

```text
Seeed Studio XIAO ESP32S3
```

## Why Knowledge Distillation

A large 27-class FSC22 model already exists from dissertation work. Instead of deploying the large model, it will be used offline as a Teacher to create soft binary labels.

The embedded Student will be much smaller and binary.

## Important Decision

We do not deploy a 27-class Student unless the project requirement changes. The edge device only needs bird / non-bird detection.
