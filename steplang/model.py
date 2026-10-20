from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class StepSyntaxError(ValueError):
    def __init__(self, message: str, *, line: int | None = None, source: str = "", text: str = ""):
        self.message = message
        self.line = line
        self.source = source
        self.text = text
        super().__init__(self.format())

    def format(self) -> str:
        if self.line is None:
            return self.message
        where = f"{self.source}:{self.line}" if self.source else f"line {self.line}"
        detail = f"\n    {self.text}" if self.text else ""
        return f"{where}: {self.message}{detail}"


@dataclass(slots=True)
class Block:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {"t": self.kind, **self.data}


@dataclass(slots=True)
class Step:
    id: str
    title: str
    blocks: list[Block] = field(default_factory=list)
    next: str | None = None
    time: str | None = None
    line: int = 0

    @property
    def has_choices(self) -> bool:
        return any(block.kind == "choice" for block in self.blocks)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "next": self.next,
            "time": self.time,
            "blocks": [block.to_dict() for block in self.blocks],
        }


@dataclass(slots=True)
class Document:
    title: str
    id: str
    description: str = ""
    version: str = "1"
    lang: str = "zh-CN"
    accent: str = "#2563eb"
    start: str | None = None
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def step(self, step_id: str) -> Step | None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "version": self.version,
            "lang": self.lang,
            "accent": self.accent,
            "start": self.start,
            "steps": [step.to_dict() for step in self.steps],
        }
