import os
from enum import Enum


class SetupType(Enum):
    LRU = "cachelib-lru"
    LRU2Q = "cachelib-lru2q"
    OVERHEAD = "cachelib-overhead"
    HOLPACA = "holpaca"
    HOLPACA_OVERHEAD = "holpaca-overhead"


class Setup:
    def __init__(
        self,
        name,
        setup_type,
        config,
        orchestrator_args=[],
    ):
        if not isinstance(setup_type, SetupType):
            raise ValueError("setup_type must be an instance of SetupType Enum")
        self.name = name
        self.setup_type = setup_type
        self.config = config
        self.orchestrator_args = orchestrator_args
        self.orchestrator_address = self.config.get(
            "holpaca.orchestrator.address", None
        )

    def cmd(self, executable, status=None):
        if not os.path.isfile(executable):
            raise FileNotFoundError(f"Executable not found: {executable}")
        return f"{executable} -load -run -db {self.setup_type.value} {f'-s {status}' if status else ''} {' '.join(f'-p {k}={v}' for k, v in self.config.items())}"

    def __copy__(self):
        return Setup(
            self.name,
            self.setup_type,
            self.config.copy(),
            self.orchestrator_args.copy(),
        )
