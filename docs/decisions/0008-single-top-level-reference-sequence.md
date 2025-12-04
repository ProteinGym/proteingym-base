# 8. Single top-level reference sequence

Date: 2025-12-04
Status: Accepted

## Context and Problem Statement

Some models need a reference sequence to make predictions about the effects of variants. For example, [Meier et al. (2021)](https://www.biorxiv.org/content/10.1101/2021.07.09.450648v) define their "masked marginal" as the difference between the log-likelihood of an alternative token at a given position and that of the token in the reference sequence. For this to be computable, we need the identity of that reference sequence.

Should we support more than one reference sequence?

## Decision

A dataset can have one reference sequence at the top-level of the manifest.

## Decision Drivers

- The use-case illustrated in Meier et al. should be supported 
- A reference sequence is often defined arbitrarily - we may want to allow for annotating more than one sequence as 'reference'

## Options

1. Name a single sequence as the reference sequence at the top level
2. Create a new sequence type - 'reference' - and enable any number of sequences to have that status 

## Decision matrix 

| Option                      | Supports 'masked marginals' | Future use-cases |
|-----------------------------|-----------------------------|------------------|
| Single at top-level         | High                        | Low              |
| Multiple with sequence type | Low                         | Medium           |

## Consequences

You can be sure to get a single sequence to use when you want to compute masked marginals and similar statistics. When future needs arise, we can still add the option to tag more sequences to have the reference status.
