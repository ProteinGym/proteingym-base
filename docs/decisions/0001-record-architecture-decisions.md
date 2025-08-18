# 1. Record architecture decisions

Date: 2025-08-14
Status: Accepted

## Context and Problem Statement

We need to record the architectural decisions made on this project.

## Decision

We will use Architecture Decision Records, as [described by Michael Nygard](http://thinkrelevance.com/blog/2011/11/15/documenting-architecture-decisions).

## Decision Drivers

- Clarity: We need a clear and consistent way to document decisions.
- Traceability: We need to be able to trace back decisions to their context and
  drivers.
- Collaboration: We need a format that allows team members to contribute and
  review decisions easily.
- Simplicity: The format should be simple enough to encourage regular use
  without being burdensome. 
- Low barrier to entry: The format should be easy to adopt without requiring
  significant changes to existing workflows.

## Considered Options

- Markdown file: Use a simple text file format to document decisions.
  - Dedicated tool: Use a specialized tool for managing architecture decisions.
- Wiki: Use a wiki platform to document decisions.

## Decision matrix

| Option                              | Clarity | Traceability | Collaboration | Simplicity | Low barrier to entry |
| ----------------------------------- | ------- | ------------ | ------------- | ---------- | -------------------- |
| Markdown file in git                | High    | High         | High          | Medium     | High                  |
| Previous option with dedicated tool | High    | High         | High          | High       | Medium                |
| Wiki                                | High    | Medium       | Medium        | Low        | Low                   |

[adr-tools](https://github.com/npryce/adr-tools) is chosen as dedicated tool
option to automate handling ADRs.

The wiki option was not chosen due to its lower traceability and barrier to
entry than git, which fits better with our existing workflows.

## Consequences

See Michael Nygard's article, linked above. For a lightweight ADR toolset, see Nat Pryce's [adr-tools](https://github.com/npryce/adr-tools).
