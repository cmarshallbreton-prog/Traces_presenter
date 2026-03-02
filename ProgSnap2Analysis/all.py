# run_all.py
import subprocess, sys

READ = r"C:\Users\chris\Desktop\Code\TracesPresenter\Traces_presenter\ProgSnap2Analysis"
OUT  = r"C:\Users\chris\Desktop\Code\TracesPresenter\Traces_presenter\ProgSnap2Analysis\out"
GAP_MIN = "5"  # minutes

cmds = [
    [sys.executable, "time_to_score1.py",  READ, rf"{OUT}\Time_To_Score1.csv"],
    [sys.executable, "compile_span.py",  READ, rf"{OUT}\Compile_Span.csv"],
    [sys.executable, "first_compile_vs_global_first.py",  READ, rf"{OUT}\First_Compile.csv"],
    [sys.executable, "last_compile_vs_global_last.py",  READ, rf"{OUT}\Last_Compile.csv"],
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