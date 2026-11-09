import threading

from nexusrag.embedder import DENSE_DIM, SparseVec
from nexusrag.index import Index


def _point(n: int) -> tuple[list[float], SparseVec]:
    dense = [0.0] * DENSE_DIM
    dense[n % DENSE_DIM] = 1.0
    return dense, SparseVec(indices=[n % 50], values=[1.0])


def test_concurrent_upserts_share_one_local_qdrant_connection(tmp_path):
    index = Index(tmp_path / "qdrant")
    errors: list[BaseException] = []

    def work(n: int) -> None:
        try:
            dense, sparse = _point(n)
            index.delete_source(f"src-{n}")
            index.upsert(
                f"src-{n}",
                [{"text": f"chunk {n}", "position": {"page": 1}}],
                [dense],
                [sparse],
            )
            index.search(dense, sparse, {f"src-{n}"}, k=1)
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=work, args=(i,)) for i in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert errors == []
    assert index.ready()
    for i in range(8):
        assert index.count_source(f"src-{i}") == 1
    index.close()
