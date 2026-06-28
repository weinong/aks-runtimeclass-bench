## ADDED Requirements

### Requirement: Default runtime baseline benchmark execution
The benchmark suite SHALL include the default Kubernetes runtime as an automatic benchmark baseline with no configured runtime class.

#### Scenario: Run baseline when benchmarking an explicit runtime class
- **WHEN** an operator runs the benchmark target with `RUNTIME_CLASS` set to an explicit runtime class
- **THEN** the suite runs a default-runtime baseline with no `runtimeClassName` and also runs the requested explicit runtime class benchmark

#### Scenario: Run only baseline when no runtime class is selected
- **WHEN** an operator runs the benchmark target with `RUNTIME_CLASS` unset
- **THEN** the suite runs the default-runtime benchmark once and does not duplicate the same baseline run

#### Scenario: Keep benchmark outputs separate
- **WHEN** the benchmark target runs both the default baseline and an explicit runtime class benchmark
- **THEN** the suite writes each run's raw metrics and JSON/CSV summaries to distinct output locations

#### Scenario: Label baseline summaries
- **WHEN** the default-runtime baseline summary is extracted
- **THEN** the suite labels the runtime class value as `standard`
