from utils.experiment import Experiment
from utils.setup import Setup, SetupType

THREADS = 4

base_config = {
    "threadcount": THREADS,
    "cleanupafterload": "true",
    "sleepafterload": 0,
    "operationcount.0": 38172843,
    "operationcount.1": 42595633,
    "operationcount.2": 8190523,
    "operationcount.3": 6738939,
    "status.interval": 1,
    "sleepafterload": 0,
    "cachelib.size.0": int(4_500_000_000 * 0.048),
    "cachelib.size.1": int(4_500_000_000 * 0.078),
    "cachelib.size.2": int(4_500_000_000 * 0.249),
    "cachelib.size.3": int(4_500_000_000 * 0.625),
    **{f"cachelib.name.{i}": f"instance-{i}" for i in range(THREADS)},
    "cachelib.pool.relsize": 1,
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

baseline = Setup(
    "baseline",
    SetupType.LRU,
    base_config,
)

optimizer = Setup(
    "optimizer",
    SetupType.LRU2Q,
    {
        **base_config,
        "cachelib.pooloptimizer": "on",
        "cachelib.poolresizer": "on",
        "cachelib.poolresizer.slabs": 1000,
    },
)

OVERHEAD_FACTOR = 1.2
SUM_CACHE_SIZE = (
    sum(base_config[f"cachelib.size.{i}"] for i in range(THREADS)) * OVERHEAD_FACTOR
)

holpaca = Setup(
    "holpaca",
    SetupType.HOLPACA,
    {
        **base_config,
        "cachelib.size.0": SUM_CACHE_SIZE,
        "cachelib.size.1": SUM_CACHE_SIZE,
        "cachelib.size.2": SUM_CACHE_SIZE,
        "cachelib.size.3": SUM_CACHE_SIZE,
        "holapca.virtualsize.0": base_config["cachelib.size.0"],
        "holapca.virtualsize.1": base_config["cachelib.size.1"],
        "holapca.virtualsize.2": base_config["cachelib.size.2"],
        "holapca.virtualsize.3": base_config["cachelib.size.3"],
        "cachelib.pool.relsize.0": base_config["cachelib.size.0"] / SUM_CACHE_SIZE,
        "cachelib.pool.relsize.1": base_config["cachelib.size.1"] / SUM_CACHE_SIZE,
        "cachelib.pool.relsize.2": base_config["cachelib.size.2"] / SUM_CACHE_SIZE,
        "cachelib.pool.relsize.3": base_config["cachelib.size.3"] / SUM_CACHE_SIZE,
        "cachelib.poolresizer": "on",
        "cachelib.poolresizer.slabs": 1000,
        "holpaca.orchestrator.address": "localhost:11110",
        **{"holpaca.agent.address.{i}": f"localhost:{11111+i}" for i in range(THREADS)},
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
    name="use_case_2",
    setups={
        "baseline": baseline,
        "optimizer": optimizer,
        "holpaca": holpaca,
    },
    override_timeout=override_timeout,
    override_num_ops=override_num_ops,
    override_objsize=override_objsize,
    override_cache_size=override_cache_size,
    status="INSERT-PASSED INSERT-FAILED READ-PASSED READ-FAILED ALL",
)
