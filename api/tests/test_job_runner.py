import threading

from nexusrag.jobs import JobRunner


def test_submitted_job_runs_in_background_and_join_waits():
    runner = JobRunner()
    gate = threading.Event()
    done = []

    def work():
        gate.wait(timeout=5)
        done.append(1)

    runner.submit(work)
    assert done == []          # submit returned before work finished
    gate.set()
    runner.join()
    assert done == [1]
    runner.shutdown()


def test_failing_job_does_not_break_the_runner():
    runner = JobRunner()
    results = []

    def boom():
        raise RuntimeError("nope")

    runner.submit(boom)
    runner.submit(lambda: results.append("ok"))
    runner.join()
    assert results == ["ok"]
    runner.shutdown()
