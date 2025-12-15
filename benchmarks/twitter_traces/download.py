import os
import subprocess
from pathlib import Path

# Configuration
DIR = Path(__file__).resolve().parent.absolute()
GetURL = (
    lambda trace_id: f"https://ftp.pdl.cmu.edu/pub/datasets/twemcacheWorkload/open_source/cluster{trace_id}.sort.zst"
)

# Define the list of specific IDs to process
traces = {
    18: 270_000_000,
    53: 180_000_000,
    40: 90_000_000,
    19: 90_000_000,
}

for trace_id, max_ops in traces.items():
    print(f"Cluster {trace_id}: {max_ops} operations")
    trace_file = DIR / f"cluster{trace_id}"
    trace_file_keyed = DIR / f"cluster{trace_id}-keyed"

    download_proc = subprocess.Popen(
        f"wget --timeout=0 -q -O - {GetURL(trace_id)} | zstdcat | pv -l -s {max_ops} | head -n {max_ops} > {trace_file}",
        shell=True,
        stdout=subprocess.PIPE,
    )

    # Process with awk-like logic
    with open(trace_file, "w") as outfile:
        for line in download_proc.stdout:
            line = line.rstrip("\n")
            fields = line.split(",")

            if len(fields) == 7:
                # Line is fine as-is
                outfile.write(line + "\n")
            elif len(fields) > 7:
                # Reconstruct the key field
                key_parts = fields[1 : len(fields) - 5]
                key = ",".join(key_parts)

                # Reconstruct the line
                result = [fields[0], key] + fields[-5:]
                outfile.write(",".join(result) + "\n")

    download_proc.wait()

    print(f"Generating keyed trace file: {trace_file_keyed}")

    # Keep only the first occurrence of each key (field 2)
    seen_keys = set()
    with open(trace_file, "r") as infile, open(trace_file_keyed, "w") as outfile:
        for line in infile:
            fields = line.rstrip("\n").split(",")
            if len(fields) >= 2:
                key = fields[1]
                if key not in seen_keys:
                    seen_keys.add(key)
                    outfile.write(line)
