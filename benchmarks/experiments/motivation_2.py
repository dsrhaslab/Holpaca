from utils.experiment import Experiment
from utils.setup import Setup, SetupType

THREADS = 4
OVERHEAD_FACTOR = 1.2

base_config = {
    "threadcount": THREADS,
    "cleanupafterload": "true",
    "sleepafterload": 0,
    "operationcount.0": 452_566_125,
    "operationcount.1": 37_095_511,
    "operationcount.2": 19_523_431,
    "operationcount.3": 17_148_591,
    "recordcount": 20_000_000,
    "request_key_domain_end": 19_999_999,
    "status.interval": 1,
    "readallfields": "false",
    "fieldcount": 1,
    "fieldlength": 1000,
    "insertorder": "nothashed",
    "requestdistribution": "zipfian",
    "zipfian_const.0": 1.2,
    "zipfian_const.1": 0.9,
    "zipfian_const.2": 0.6,
    "requestdistribution.3": "uniform",
    "sleepafterload": 0,
    "cachelib.size": 2_000_000_000,
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
    "workload.type": "synthetic",
    "readproportion": 1,
    "updateproportion": 0,
    "scanproportion": 0,
    "insertproportion": 0,
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

custom = Setup(
    "custom",
    SetupType.HOLPACA,
    {
        **base_config,
        "holpaca.virtualsize": 2_000_000_000,
        "holpaca.size": 2_000_000_000 * THREADS * OVERHEAD_FACTOR,
        "cachelib.poolresizer": "on",
        "cachelib.poolresizer.slabs": 1000,
        "holpaca.pool.noinitialsize": "on",
        "holpaca.pool.proportion.0": 0.91,
        "holpaca.pool.proportion.1": 0.03,
        "holpaca.pool.proportion.2": 0.03,
        "holpaca.pool.proportion.3": 0.03,
        "holpaca.orchestrator.address": "localhost:11110",
        # Each thread has a different instance, thus different agents
        **{
            f"holpaca.agent.address.{i}": f"localhost:{11111+i}" for i in range(THREADS)
        },
    },
    orchestrator_args=["Motivation", "1000"],
)


def override_timeout(config, timeout):
    config["maxexecutiontime"] = timeout
    for i in range(THREADS):
        config.pop(f"maxexecutiontime.{i}", None)


def override_objsize(config, size, thread=None):
    config["fieldlength"] = size
    for i in range(THREADS):
        config.pop(f"fieldlength.{i}", None)


def override_num_ops(config, num_ops, thread=None):
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
        # the cache must accommodate space from other pools if needed, and an overhead since cachelib provides less space than requested
        config["cachelib.size"] = cache_size * THREADS * OVERHEAD_FACTOR
        config["holpaca.virtualsize"] = cache_size / THREADS
        for i in range(THREADS):
            config.pop(f"holpaca.virtualsize.{i}", None)
            config.pop(f"cachelib.size.{i}", None)
    else:
        config["cachelib.size"] = cache_size
        for i in range(THREADS):
            config.pop(f"cachelib.size.{i}", None)


EXPERIMENT = Experiment(
    name="motivation_2",
    setups={
        "baseline": baseline,
        "custom": custom,
        "optimizer": optimizer,
    },
    override_timeout=override_timeout,
    override_num_ops=override_num_ops,
    override_objsize=override_objsize,
    override_cache_size=override_cache_size,
    status="READ-PASSED READ-FAILED ALL",
)
