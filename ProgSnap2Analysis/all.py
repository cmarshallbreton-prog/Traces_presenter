# run_all.py
import subprocess, sys

READ = r"C:\Users\chris\Desktop\Code\TracesPresenter\Traces_presenter\ProgSnap2Analysis"
OUT  = r"C:\Users\chris\Desktop\Code\TracesPresenter\Traces_presenter\ProgSnap2Analysis\out"
GAP_MIN = "5"  # minutes

cmds = [
    [sys.executable, "compile_count.py",  READ, rf"{OUT}\CompileCount.csv"],
    [sys.executable, "session_count.py",  READ, rf"{OUT}\SessionCount.csv", GAP_MIN],
    [sys.executable, "frac_long.py",      READ, rf"{OUT}\FracLong.csv", GAP_MIN],
    [sys.executable, "mean_test_score.py",     READ, rf"{OUT}\MeanTest.csv"],
    [sys.executable, "compil_ratio.py",   READ, rf"{OUT}\CompilPassFailRatio.csv"],
    [sys.executable, "eq.py",             READ, rf"{OUT}\EQ.csv"],
    [sys.executable, "red.py",            READ, rf"{OUT}\RED.csv"],
]

for c in cmds:
    subprocess.run(c, check=True)
print("OK")