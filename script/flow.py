from argparse import ArgumentParser
from collections.abc import Iterable
from collections import defaultdict
from dataclasses import dataclass
from graphlib import TopologicalSorter
from pathlib import Path
import sys
from typing import Self


@dataclass(slots=True)
class Flow:

    source: str
    target: str
    weight: float
    color: None | str

    @classmethod
    def of(cls, s: str) -> Self:
        source, _, rest = s.strip().partition("[")
        if rest is None:
            raise ValueError(f'invalid flow "{s}"')

        w, _, rest = rest.partition("]")
        try:
            weight = float(w)
        except:
            raise ValueError(f'invalid weight "{s}"')
        if rest is None:
            raise ValueError(f'invalid flow "{s}"')

        target, _, color = rest.rpartition("#")
        if target is None:
            target = color
        else:
            color = f"#{color.strip()}"

        return cls(
            source=source.strip(),
            target=target.strip(),
            weight=weight,
            color=color,
        )

    def scale_in_place(self, factor: float) -> None:
        self.weight *= factor


@dataclass(slots=True)
class Graph:

    nodes: frozenset[str]
    flows: tuple[Flow, ...]
    stages: tuple[tuple[str], ...]
    sources: frozenset[str]
    sinks: frozenset[str]

    @classmethod
    def _parse_lines(cls, lines: Iterable[str]) -> tuple[set[str], list[Flow]]:
        nodes = set()
        flows = []

        for line in lines:
            line = line.strip()
            if line == "" or line.startswith("#") or line.startswith("//"):
                continue

            flow = Flow.of(line)
            nodes.add(flow.source)
            nodes.add(flow.target)
            flows.append(flow)

        return nodes, flows

    @classmethod
    def _sort_into_stages(cls, flows: Iterable[Flow]) -> list[tuple[str]]:
        graph = defaultdict(set)
        for flow in flows:
            predecessors = graph[flow.target]
            predecessors.add(flow.source)

        sorter = TopologicalSorter(graph)
        sorter.prepare()

        stages = []
        while sorter:
            stage = sorter.get_ready()
            stages.append(stage)
            sorter.done(*stage)

        return stages

    @classmethod
    def _delay_stages(cls, flows: list[Flow], stages: list[tuple[str]]) -> None:
        need_placement = set(stages[0])
        for index, stage in enumerate(stages):
            if index == 0:
                continue

            also_needs_placement = set([] if index == 1 else stages[index - 1])
            updated_stage = []
            current_stage = set(stage)

            for flow in flows:
                if not flow.target in current_stage:
                    continue
                if flow.source in need_placement:
                    updated_stage.append(flow.source)
                    need_placement.remove(flow.source)
                if flow.source in also_needs_placement:
                    updated_stage.append(flow.source)
                    also_needs_placement.remove(flow.source)

            if 0 < len(also_needs_placement):
                updated_stage.extend(also_needs_placement)
            if 0 < len(updated_stage):
                stages[index - 1] = tuple(updated_stage)
                if len(need_placement) == 0:
                    break

    @classmethod
    def _winnow_sinks(cls, not_sources: set[str], flows: list[Flow]) -> set[str]:
        for flow in flows:
            if flow.source in not_sources:
                not_sources.remove(flow.source)
        return not_sources

    @classmethod
    def of(cls, lines: Iterable[str]) -> Self:
        nodes, flows = cls._parse_lines(lines)
        stages = cls._sort_into_stages(flows)
        sources = frozenset(stages[0])
        sinks = frozenset(cls._winnow_sinks(nodes - sources, flows))
        cls._delay_stages(flows, stages)
        return cls(
            nodes=frozenset(nodes),
            flows=tuple(flows),
            stages=tuple(stages),
            sources=sources,
            sinks=sinks,
        )


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("spec", help="the specification with the flow")
    options = parser.parse_args(sys.argv[1:])
    graph = Graph.of(Path(options.spec).read_text("utf8").splitlines())

    print("----- Sources ".rjust(80, "-"))
    for source in graph.sources:
        print(source)
    print("----- Sinks ".rjust(80, "-"))
    for sink in graph.sinks:
        print(sink)
    print("----- Stages ".rjust(80, "-"))
    for stage in graph.stages:
        print(stage)
