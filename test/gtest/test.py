from test_data import matrix_sizes
import subprocess
import csv
import pandas as pd
import statistics

def generate_command(m, n, k):
    base_cmd = "HIP_VISIBLE_DEVICES=4 /src/hipSPARSELt/build/release/clients/staging/hipsparselt-bench -f compress -r f16_r -i 100 -j 10 -v 1"
    return f"{base_cmd} -m {m} -n {n} -k {k} --order R"
def generate_baseline_command(m, n, k):
    base_cmd = "HIP_VISIBLE_DEVICES=4 /src/hipSPARSELt/build/release/clients/staging/hipsparselt-bench -f compress -r f16_r -i 100 -j 10 -v 1"
    return f"{base_cmd} -m {m} -n {n} -k {k} --SG0I -1 --SG1J -1 --TT0I -1 --TT1J -1 --order R"

def get_median_performance(command, num_runs=10):
    """
    Run the command multiple times and return the median performance.
    """
    performances = []
    for i in range(num_runs):
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            last_line = result.stdout.strip().split('\n')[-1]
            performance = float(last_line.split(',')[-4])
            performances.append(performance)
        else:
            print(f"Error in run {i+1}: {result.stderr}")
            return None
    
    if performances:
        return round(statistics.median(performances), 2)
    return None
def run_test():
    # Open new output file in write mode
    with open('./test_results/comparison_results_fix.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        # Write header row with baseline and comparison info
        writer.writerow(['M', 'N', 'K', 'Baseline_Performance', 'Current_Performance', 'Difference', 'Percent_Change'])
        
        for matrix in matrix_sizes:
            m, n, k = matrix["M"], matrix["N"], matrix["K"]
            command = generate_command(m, n, k)
            baseline_command = generate_baseline_command(m, n, k)
            print(f"Running current tests for matrix {m}x{n}x{k}...")
            
            try:
                # Get baseline performance for this matrix size
                baseline_perf = get_median_performance(baseline_command)
    
                if baseline_perf is not None:
                    # Run current test multiple times
                    current_perf = get_median_performance(command)
                    
                    if current_perf is not None:
                        # Calculate differences
                        abs_diff = current_perf - baseline_perf
                        percent_change = (abs_diff / baseline_perf) * 100
                
                    
                    # Write results to CSV
                    writer.writerow([
                        m, n, k,
                        baseline_perf,
                        current_perf,
                        round(abs_diff, 2),
                        round(percent_change, 2)
                    ])
                    
                    # Print progress with comparison
                    print(f"Matrix {m}x{n}x{k}:")
                    print(f"  Baseline: {baseline_perf:.2f}")
                    print(f"  Current:  {current_perf:.2f}")
                    print(f"  Change:   {percent_change:+.2f}%")
                    print("---")
                    
                else:
                    print(f"Error running test for matrix size {m}x{n}x{k}: {result.stderr}")
                    
            except Exception as e:
                print(f"Exception occurred for matrix size {m}x{n}x{k}: {str(e)}")

if __name__ == "__main__":
    run_test()