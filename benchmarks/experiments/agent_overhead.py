from utils.experiment import Experiment
from utils.setup import Setup, SetupType

OVERHEAD_FACTOR = 1.2

READ_ONLY = {
    "readproportion": 1,
    "updateproportion": 0,
    "scanproportion": 0,
    "insertproportion": 0,
}

MIXED = {
    "readproportion": 0.5,
    "updateproportion": 0.5,
    "scanproportion": 0,
    "insertproportion": 0,
}

WRITE_HEAVY = {
    "readproportion": 0.1,
    "updateproportion": 0.9,
    "scanproportion": 0,
    "insertproportion": 0,
}


TENANTS = lambda threads, keys, objsize: {
    "cachelib.size": keys * objsize * threads * OVERHEAD_FACTOR,
    "cachelib.name": "instance-0",
    "cachelib.pool.relsize": 1 / threads,
    **{f"cachelib.pool.name.{i}": f"p{i}" for i in range(threads)},
}

INSTANCES = lambda threads, keys, objsize: {
    "cachelib.size": keys * objsize * OVERHEAD_FACTOR,
    **{f"cachelib.name.{i}": f"instance-{i}" for i in range(threads)},
    "cachelib.pool.relsize": 1,
    "cachelib.pool.name.0": "p0",
}


BASE_CONFIG = lambda threads: {
    "threadcount": threads,
    "cleanupafterload": "false",
    "operationcount": 100_000_000_000,
    "maxexecutiontime": 600,
    "sleepafterload": 0,
    "recordcount": 2_000_000,
    "request_key_domain_end": 1_999_999,
    **{f"request_key_prefix.{i}": f"p{i}" for i in range(threads)},
    "status.interval": 1,
    "readallfields": "false",
    "fieldcount": 1,
    "fieldlength": 1000,
    "insertorder": "nothashed",
    "requestdistribution": "uniform",
    "workload.type": "synthetic",
}

BUILD_CACHELIB = lambda name, config: Setup(name, SetupType.OVERHEAD, config)

BUILD_HOLPACA = lambda name, config: Setup(
    name,
    SetupType.HOLPACA_OVERHEAD,
    {
        **config,
        "holpaca.orchestrator.address": "localhost:11110",
        **{
            f"holpaca.agent.address.{i}": f"localhost:{11111+i}"
            for i in range(config["threadcount"])
        },
    },
    orchestrator_args=["ThroughputMaximization", "1000:0.01:true"],
)


BUILD_TYPES = {"cachelib": BUILD_CACHELIB, "holpaca": BUILD_HOLPACA}

setups = {}
workloads = {"read-only": READ_ONLY, "mixed": MIXED, "write-heavy": WRITE_HEAVY}
setup_types = {"tenants": TENANTS, "instances": INSTANCES}
threads = [1, 2, 4, 8, 16, 32]
runs = 1

for build_name, build_type in BUILD_TYPES.items():
    for setup_type_name, setup_type in setup_types.items():
        for workload_name, workload in workloads.items():
            for thread in threads:
                base_config = BASE_CONFIG(thread)
                for run in range(runs):
                    name = f"{build_name}_{setup_type_name}_{workload_name}_{thread}_{run+1}"
                    setups[name] = build_type(
                        name,
                        {
                            **base_config,
                            **setup_type(
                                thread,
                                base_config["recordcount"],
                                base_config["fieldlength"],
                            ),
                            **workload,
                        },
                    )


def override_timeout(config, timeout):
    config["maxexecutiontime"] = timeout


def override_objsize(config, size, thread=None):
    config["fieldlength"] = size


def override_num_ops(config, num_ops, thread=None):
    config["operationcount"] = num_ops


def override_cache_size(config, cache_size):
    config["cachelib.size"] = cache_size


EXPERIMENT = Experiment(
    name="agent_overhead",
    setups=setups,
    override_timeout=override_timeout,
    override_num_ops=override_num_ops,
    override_objsize=override_objsize,
    override_cache_size=override_cache_size,
    status="INSERT-PASSED INSERT-FAILED READ-PASSED READ-FAILED ALL",
    no_db=True,
)
