from utils.experiment import Experiment
from utils.setup import Setup, SetupType

THREADS = 4
OVERHEAD_FACTOR = 1.2
VIRTUAL_SIZE = 4_500_000_000
CACHE_SIZE = VIRTUAL_SIZE * THREADS * OVERHEAD_FACTOR

base_config = {
    "threadcount": THREADS,
    "cleanupafterload": "true",
    "sleepafterload": 0,
    "operationcount": 1_000_000_000_000,
    "maxexecutiontime": 3600,
    "status.interval": 1,
    "sleepafterload": 0,
    "cachelib.poolresizer": "on",
    "cachelib.poolresizer.slabs": 1000,
    "cachelib.size": CACHE_SIZE,
    "holapca.virtualsize.0": VIRTUAL_SIZE * 0.048,
    "holapca.virtualsize.1": VIRTUAL_SIZE * 0.078,
    "holapca.virtualsize.2": VIRTUAL_SIZE * 0.249,
    "holapca.virtualsize.3": VIRTUAL_SIZE * 0.625,
    "cachelib.pool.relsize.0": VIRTUAL_SIZE * 0.048 / CACHE_SIZE,
    "cachelib.pool.relsize.1": VIRTUAL_SIZE * 0.078 / CACHE_SIZE,
    "cachelib.pool.relsize.2": VIRTUAL_SIZE * 0.249 / CACHE_SIZE,
    "cachelib.pool.relsize.3": VIRTUAL_SIZE * 0.625 / CACHE_SIZE,
    "holpaca.orchestrator.address": "localhost:11110",
    **{"holpaca.agent.address.{i}": f"localhost:{11111+i}" for i in range(THREADS)},
    **{f"cachelib.name.{i}": f"instance-{i}" for i in range(THREADS)},
    **{f"cachelib.pool.name.{i}": f"p{i}" for i in range(THREADS)},
    **{f"request_key_prefix.{i}": f"p{i}" for i in range(THREADS)},
    # rocksdb
    "rocksdb.compression": "no",
    "rocksdb.write_buffer_size": 134217728,
    "rocksdb.max_write_buffer_number": 2,
    "rocksdb.level0_file_number_compaction_trigger": 4,
    "rocksdb.max_background_flushes": 1,
    "rocksdb.max_background_compactions": 3,
    "rocksdb.use_direct_reads": "true",
    "rocksdb.no_block_cache": "true",
    "rocksdb.use_direct_io_for_flush_compaction": "true",
    # workload
    "workload.type": "trace",
    "trace.override_value_size": 1000,
    "trace.runfile.0": "cluster18",
    "trace.loadfile.0": "cluster18-keyed",
    "trace.runfile.1": "cluster53",
    "trace.loadfile.1": "cluster53-keyed",
    "trace.runfile.2": "cluster40",
    "trace.loadfile.2": "cluster40-keyed",
    "trace.runfile.3": "cluster19",
    "trace.loadfile.3": "cluster19-keyed",
}


OVERHEAD_FACTOR = 1.2

h_base = Setup(
    "H_base",
    SetupType.HOLPACA,
    {
        **base_config,
        "cachelib.pool.qos.0": 12_253.194,
        "cachelib.pool.qos.1": 13_330.939,
        "cachelib.pool.qos.2": 2_313.967,
        "cachelib.pool.qos.3": 1_953.826,
    },
    orchestrator_args=["ThroughputMaximization", "1000:0.01"],
)
h_i_1 = Setup(
    "H_I_1",
    SetupType.HOLPACA,
    {
        **base_config,
        "cachelib.pool.qos.0": 60_000.0,
        "cachelib.pool.qos.1": 5_000.0,
        "cachelib.pool.qos.2": 1_000.0,
        "cachelib.pool.qos.3": 1_000.0,
    },
    orchestrator_args=["ThroughputMaximization", "1000:0.01"],
)
h_i_2 = Setup(
    "H_I_2",
    SetupType.HOLPACA,
    {
        **base_config,
        "holpaca.pool.qos.0": 5_000.0,
        "holpaca.pool.qos.1": 50_000.0,
        "holpaca.pool.qos.2": 1_000.0,
        "holpaca.pool.qos.3": 1_000.0,
    },
    orchestrator_args=["ThroughputMaximization", "1000:0.01"],
)


def override_timeout(config, timeout):
    config["maxexecutiontime"] = timeout
    for i in range(THREADS):
        config.pop(f"maxexecutiontime.{i}", None)


def override_objsize(config, size):
    config["trace.override_value_size"] = size
    for i in range(THREADS):
        config.pop(f"trace.override_value_size.{i}", None)


def override_num_ops(config, num_ops):
    config["operationcount"] = num_ops
    for i in range(THREADS):
        config.pop(f"operationcount.{i}", None)


def has_virtual_size(config):
    if "holpaca.virtualsize" in config:
        return True
    for i in range(THREADS):
        if f"holpaca.virtualsize.{i}" in config:
            return True
    return False


def override_cache_size(config, cache_size):
    if has_virtual_size(config):
        config[f"holpaca.virtualsize"] = cache_size
        config[f"cachelib.size"] = cache_size * THREADS * OVERHEAD_FACTOR
        config[f"cachelib.pool.relsize"] = 1
        for i in range(THREADS):
            config.pop(f"holpaca.virtualsize.{i}", None)
            config.pop(f"cachelib.size.{i}", None)
            config.pop(f"cachelib.pool.relsize.{i}", None)
    else:
        config["cachelib.size"] = cache_size / THREADS
        config["cachelib.pool.relsize"] = 1
        for i in range(THREADS):
            config.pop(f"cachelib.size.{i}", None)
            config.pop(f"cachelib.pool.relsize.{i}", None)


EXPERIMENT = Experiment(
    name="use_case_3",
    setups={
        "H_base": h_base,
        "H_I_1": h_i_1,
        "H_I_2": h_i_2,
    },
    override_timeout=override_timeout,
    override_num_ops=override_num_ops,
    override_objsize=override_objsize,
    override_cache_size=override_cache_size,
    status="INSERT-PASSED INSERT-FAILED READ-PASSED READ-FAILED ALL",
)
