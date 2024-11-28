import itertools
from pathlib import Path
import subprocess
from typing import Dict, Set, List, Tuple
import argparse
import logging
from datetime import datetime
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('benchmark.log'),
        logging.StreamHandler()
    ]
)

def get_completed_sizes(result_file) -> Set[str]:
    """
    Read existing results and return a set of sizes that have been tested.
    Format example: {1024, 8, 1024, 16, 32, 2, 8}
    """
    completed_sizes = set()
    if result_file.exists():
        with open(result_file, 'r') as f:
            next(f, None)  # Skip header
            for line in f:
                # Remove curly braces and split by comma
                line = line.strip().strip('{}')
                if not line:
                    continue
                parts = [p.strip() for p in line.split(',')]
                if len(parts) >= 3:  # Need m, n, k values
                    m, n, k = parts[0], parts[1], parts[2]
                    completed_sizes.add(f"{m}x{k}")
    return completed_sizes

def generate_grid_points(start_m: int, start_k: int, max_m: int = 102400, max_k: int = 102400) -> List[Tuple[int, int]]:
    print(f"Generating grid points for m in range {start_m}-{max_m} and k in range {start_k}-{max_k}")
    grid_points = []
    for x in range(start_m, max_m+1):
        for y in range(start_k, max_k+1):
            if x <= 64 and y <= 64:
                current_stride = 8
            elif x <= 256 and y <= 256:
                current_stride = 32
            elif x <= 1024 and y <= 1024:  
                current_stride = 128
            elif x <= 4096 and y <= 4096:
                current_stride = 512
            elif x <= 16384 and y <= 16384:
                current_stride = 2048
            elif x <= 65536 and y <= 65536:
                current_stride = 8192
            else:
                current_stride = 16384
            
            if x % current_stride == 0 and y % current_stride == 0:
                grid_points.append((x, y))
    
    return grid_points

def is_valid_config(sg0i: int, sg1j: int, tt0i: int, tt1j: int) -> bool:
    """Check if a configuration is valid before running benchmark."""
    if sg0i * sg1j > 1024:  # Max threads per block
        return False
    
    MT0I = sg0i * tt0i
    MT1J = sg1j * tt1j
    
    if MT0I > 256 or MT1J > 256:
        return False
    
    return True

def run_benchmark(m: int, n: int, k: int, sg0i: int, sg1j: int, tt0i: int, tt1j: int) -> tuple:
    """Run a single benchmark configuration 5 times and return results with median performance."""
    NUM_RUNS = 10
    performances = []
    
    cmd = f"HIP_VISIBLE_DEVICES=4 /src/hipSPARSELt/build/release/clients/staging/hipsparselt-bench -f compress -r f16_r -i 1000 -j 100 -v 1 -m {m} -n {n} -k {k} --SG0I {sg0i} --SG1J {sg1j} --TT0I {tt0i} --TT1J {tt1j} --order R"
    print(f"Running command {NUM_RUNS} times: {cmd}")
    
    for run in range(NUM_RUNS):
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            last_line = result.stdout.strip().split('\n')[-1]
            performance = float(last_line.split(',')[-4])
            norm_error_1 = float(last_line.split(',')[-2])
            norm_error_2 = float(last_line.split(',')[-1])
            
            if norm_error_1 == 0 and norm_error_2 == 0:
                performances.append(performance)
                print(f"Run {run + 1} Performance: {performance}")
            time.sleep(0.1)
        except Exception as e:
            logging.error(f"Error running benchmark {cmd} (run {run + 1}): {str(e)}")
            return None
    
    # Check if we have all successful runs
    if len(performances) == NUM_RUNS:
        # Calculate median performance
        performances.sort()
        median_performance = performances[NUM_RUNS // 2]
        best_performance = performances[0]
        print(f"Best Performance: {best_performance}")
        #print(f"Median Performance: {median_performance}")
        #return (median_performance, sg0i, sg1j, tt0i, tt1j)
        return (best_performance, sg0i, sg1j, tt0i, tt1j)
    
    return None

def main():
    parser = argparse.ArgumentParser(description='Run optimized benchmarks with specified size range')
    parser.add_argument('--start', type=int,
                      help='Starting size for both M and K dimensions (e.g., 1024)')
    parser.add_argument('--end', type=int,
                      help='Ending size for both M and K dimensions (e.g., 65536)')
    parser.add_argument('--specific-m', type=int,
                      help='Specific M dimension size to test')
    parser.add_argument('--specific-k', type=int,
                      help='Specific K dimension size to test')
    parser.add_argument('--force-rerun', action='store_true',
                      help='Force rerun of all configurations, ignoring previous results')
    args = parser.parse_args()

    # Validate arguments
    if (args.start is None or args.end is None) and (args.specific_m is None or args.specific_k is None):
        parser.error("Either provide --start and --end OR --specific-m and --specific-k")
    if args.start is not None and args.specific_m is not None:
        parser.error("Cannot use both range (--start/--end) and specific size arguments simultaneously")

    # Parameter ranges - pre-filtered for common valid configurations
    sg0i_values = [16, 32, 64, 128]  # Removed 256 as it often causes invalid configs
    sg1j_values = [2, 4, 8, 16]      # Removed 32 as it often causes invalid configs
    tt0i_values = [1, 2, 4, 8]       # Removed 16 as it often causes invalid configs
    tt1j_values = [8, 16]        # These values seem to work well

    output_dir = Path("benchmark_results")
    output_dir.mkdir(exist_ok=True)
    result_file = output_dir / "benchmark_results.txt"
    temp_file = output_dir / "temp_results.txt"

    # Get set of already completed sizes
    completed_sizes = set() if args.force_rerun else get_completed_sizes(result_file)

    with open(temp_file, "w") as f:
        f.write("m,k,SG0I,SG1J,TT0I,TT1J\n")
        
        # Generate matrix sizes based on input arguments
        if args.specific_m is not None:
            matrix_sizes = [(args.specific_m, args.specific_k)]
        else:
            matrix_sizes = generate_grid_points(args.start, args.start, args.end, args.end)
            
        total_configs = len(matrix_sizes) * len(sg0i_values) * len(sg1j_values) * len(tt0i_values) * len(tt1j_values)
        logging.info(f"Total configurations to test: {total_configs}")

        for size in matrix_sizes:
            m, k = size
            n = 16
            size_str = f"{m}x{k}"
            
            # Skip if already tested and not force-rerun
            if size_str in completed_sizes and not args.force_rerun:
                logging.info(f"Skipping {size_str} - already tested")
                continue

            logging.info(f"\nTesting matrix size: {m}x{n}x{k}")
            current_best_perf = float('inf')
            best_config = None

            # Generate all valid parameter combinations
            combinations = [
                (sg0i, sg1j, tt0i, tt1j)
                for sg0i, sg1j, tt0i, tt1j in itertools.product(
                    sg0i_values, sg1j_values, tt0i_values, tt1j_values
                )
                if is_valid_config(sg0i, sg1j, tt0i, tt1j)
            ]

            for sg0i, sg1j, tt0i, tt1j in combinations:
                result = run_benchmark(m, n, k, sg0i, sg1j, tt0i, tt1j)
                if result is not None:
                    performance, sg0i, sg1j, tt0i, tt1j = result
                    if performance < current_best_perf:
                        current_best_perf = performance
                        best_config = (sg0i, sg1j, tt0i, tt1j)
            
            if best_config is not None:
                sg0i, sg1j, tt0i, tt1j = best_config
                f.write(f"{{{m}, {k}, {sg0i}, {sg1j}, {tt0i}, {tt1j}}},\n")
                f.flush()
                logging.info(f"Best configuration for {size_str}: {best_config} (Performance: {current_best_perf})")

    # Replace old result file with new one
    temp_file.replace(result_file)
    logging.info("\nBenchmarking complete. Results written to benchmark_results.txt")

if __name__ == "__main__":
    main()