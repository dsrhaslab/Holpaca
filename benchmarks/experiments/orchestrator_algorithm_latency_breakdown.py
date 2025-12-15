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

setups = {}
workloads = {"read-only": READ_ONLY, "mixed": MIXED, "write-heavy": WRITE_HEAVY}
setup_types = {"tenants": TENANTS, "instances": INSTANCES}
threads = [1, 2, 4, 8, 16, 32]

for setup_type_name, setup_type in setup_types.items():
    for workload_name, workload in workloads.items():
        for thread in threads:
            base_config = BASE_CONFIG(thread)
            name = f"holpaca_{setup_type_name}_{workload_name}_{thread}"
            setups[name] = Setup(
                name,
                SetupType.HOLPACA_OVERHEAD,
                {
                    **base_config,
                    **setup_type(
                        thread,
                        base_config["recordcount"],
                        base_config["fieldlength"],
                    ),
                    **workload,
                    "holpaca.orchestrator.address": "localhost:11110",
                    **{
                        f"holpaca.agent.address.{i}": f"localhost:{11111+i}"
                        for i in range(thread)
                    },
                },
                orchestrator_args=[
                    "ThroughputMaximization",
                    "1000:0.01:true:1000",
                ],
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
    name="orchestrator_algorithm_latency_breakdown",
    setups=setups,
    override_timeout=override_timeout,
    override_num_ops=override_num_ops,
    override_objsize=override_objsize,
    override_cache_size=override_cache_size,
    status="INSERT-PASSED INSERT-FAILED READ-PASSED READ-FAILED ALL",
    no_db=True,
)
