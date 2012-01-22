import py
import json
import sys
from runner import run_and_store


def test_run_and_store():
    tmpdir = py.test.ensuretemp('bench_runner')
    resfile = tmpdir.join('results')
    run_and_store(['startup'], resfile, sys.executable)
    assert resfile.check()
    data = json.loads(resfile.read())['results']
    assert [i[0] for i in data] == ['normal_startup', 'startup_nosite']
    assert [i[1] for i in data] == ['ComparisonResult', 'ComparisonResult']
