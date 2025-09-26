# NUMBER. TITLE

Date: 2025-09-26
Status: WIP

## Context and Problem Statement

The goal is to filter a dataset to check if it matches one or multiple conditions by CLI, for example, to find the dataset with the name `NEIME_2019`:

```
$ pg2-dataset list <path-to-your-dataset(s)> --query "name=NEIME_2019" --format json >> dataset(s).json

[
  {
    "name": "NEIME_2019",
    "description": "The NEIME Kennouche 2019 (UniProt id: A0A1I9GEU1) datase",
    "path": "/datasets/neime/NEIME_2019.pgdata"
  }
]
```

There are two phases of filtering here:

* The first is the query params, which can support the following conditions:
  * Simple fields: `name=NEIME_2019`
  * Nested fields: `assay_conditions.name=PH`
  * Multiple conditions: `name=NEIME_2019&assay_conditions.name=PH`
  * Multiple choises: `assay_conditions.name=PH,T` or `assay_conditions.name=PH&assay_conditions.name=T`

* The second is the [Dataset](../../src/pg2_dataset/dataset.py) object itself, namely `class Dataset(BaseModel)`:
  * Simple fields: `name`, `description`, etc...
  * Nested fields: `assays`, `sequences`, `structures`, `msas`, etc... of which they are also a list to loop over, which will lead to extra CPU computations.

There are several Python tools to parse the query params and the `Dataset` object, we take into account the following tools:

* [JMESPath](https://jmespath.org/)
* [jq](https://jqlang.org/)
* [urllib](https://docs.python.org/3/library/urllib.html)

To choose which tool to use, our decisions are based on the following considerations:

* Whether to use an existing tool to parse and query `Dataset` object or building it ourselves. 
  * Both `JMESPath` and `jq` support the JSON data query, and both are CLI tools and have their corresponding Python package: [jmespath.py
](https://github.com/jmespath/jmespath.py) and [jq.py](https://github.com/mwilliamson/jq.py), meaning we can either use them in CLI or integrate them inside our `proteingym-base` Python package. Besides, by using these two tools, we can parse both the query params and the serialized `Dataset` object, wherease `urllib` can only parse the query params.
  * The downsides of using these two tools are that they only support the JSON format, and we need to ensure the `Dataset` object can be serialized to JSON. Unluckily, `Bio.PDB.Structure` can't be easily serialized except for its name and metadata, whereas for `Bio.Seq.Seq` and `Bio.Align.MultipleSeqAlignment`, we need to implement its custom `field_serializer` in `Dataset`.

* Whether to parse and query `Dataset` inside our `proteingym-base` Python package or outside it in CLI. 
  * If we query it in CLI, then the command can be chained like `pg2-dataset list <path-to-your-dataset(s)> --format json | jq 'map(select(.name == "NEIME_2019"))'` using `jq`, instead of `pg2-dataset list <path-to-your-dataset(s)> --query "name=NEIME_2019" --format json`, which is much simpler.
  * For the memory and performance characteristics of using `jq` or `JMESPath` in CLI to parse serialize `Dataset`, the comparison is shown in the following table:
  
```shell
| Tool     | Memory Usage                  | Processing                         | Sweet Spot         |
| -------- | ----------------------------- | ---------------------------------- | ------------------ |
| jq       | Loads entire JSON into memory | [Stream-capable](https://jqlang.org/manual/#streaming) for some operations | < 100MB JSON files |
| JMESPath | Loads entire JSON into memory | In-memory processing               | < 50MB JSON files  |
```
  * Based on [this jq benchmark](https://github.com/jqlang/jq/wiki/X---Experimental-Benchmarks), we see that `jq` handles moderate-sized datasets (54-181MB) quite well, compared to `gojq` (Go implementation), `rq` (Rust implementation). So we infer that given 1000 datasets (likely much smaller total size), processing should be very fast under seconds. Especially with `--stream`, it can reduce memory usage from 223MB to 1.3MB for the same operation.

## Decision

Based on the above considerations, we decide to use `jq`, because of the following practicalities:

* Use JSON as the serialized format, as it is supported by the existing tools: `jq` and `JMESPath`, to parse and query.
* Add custom `field_serializer` in `Dataset` to only serialize the critical conditions, such as Structure's namd and metadata, to walk around the impossibility of serializing the whole Structure.
* Use `jq` instead of `JMESPath`, as it is more popular and is more performant for larger data with `--stream` option.
* The user needs to learn jq's query grammar, which is more complex than URL's query params, but much simpler than `JMESPath`.

## Decision Drivers

- Robustness: Use existing tools instead of building some parsing tool ourselves, which is more battle-tested.
- Simplicity: The user-facing query is simple, and moreover the code is simple to read and maintain.
- Performance: It is fast and memory efficient to parse and query larger data.

## Considered Options

* [JMESPath](https://jmespath.org/): Less simple in its own query grammar and less performant with larger data.
* [jq](https://jqlang.org/): Simple query grammar and performant with larger data.
* [urllib](https://docs.python.org/3/library/urllib.html): Only work for query params, which is simple, but we need to build tools to parse the `Dataset` object.

## Decision matrix

| Option   | Robustness | Simplicity | Performance |
| -------- | ---------- | ---------- | ----------- |
| JMESPath | High       | Medium     | Medium      |
| jq       | High       | Medium     | High        |
| urllib   | Low        | High       | Unknown     |

## Consequences

We need to write custom serializers for some fields in `Dataset`, which are `assays`, `sequences`, `structures` and `msas` for them to be serializable to JSON. 