# 0009. Deterministic Single-Pass Orchestration over Agentic Tool-Calling Loops

## Status

Accepted

## Context

A ReAct-style agent (the LLM repeatedly chooses a tool, observes the result, and decides whether to call another
tool or answer) is the default pattern for "agentic" LangGraph systems, and would let the model adaptively gather
more evidence if its first pass came up short. It also introduces real costs: unpredictable latency and token
spend, harder-to-test behavior (the path through the graph depends on model output at every step), and a much
larger surface for the model to go wrong (looping indefinitely, hallucinating tool arguments across turns).

## Decision

The reasoning pipeline (and, by the same reasoning, Insights' `AnalysisRunner`) is a fixed, linear sequence: plan
once (`RetrievalPlanner`), execute once (`RetrievalExecutor`), reason once (`ReasoningEngine`) -
`plan_retrieval -> execute_retrieval -> reason`, no cycles, no conditional edges. The LLM receives all gathered
evidence before it begins reasoning and never re-enters the retrieval stage. Multi-step retrieval exists
([0008](0008-retrieval-as-planning-and-execution.md)) but is planned up front in one shot, not discovered
iteratively.

## Consequences

A question whose first-pass evidence turns out to be insufficient gets an honest "evidence insufficient" answer
(see [0012](0012-deterministic-non-llm-answer-validation.md)'s validator, and the `evidence_sufficient` /
`limitations` fields on `ReasoningResult`) rather than the system automatically trying again with a refined query -
a real capability gap relative to a ReAct agent, accepted deliberately for predictability, testability, and cost
control. Every run of the pipeline is a fixed, inspectable sequence of exactly the calls it needs (plan, optionally
embed for semantic search, reason) - never more.
