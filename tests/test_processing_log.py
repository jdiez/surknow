"""Tests for ProcessingLog (unit tests with mocked DB)."""

from unittest.mock import AsyncMock

import pytest

from domain_kg.agents.log import ProcessingLog


@pytest.fixture
def mock_db() -> AsyncMock:
    db = AsyncMock()
    db.query = AsyncMock(return_value=[])
    db.create = AsyncMock(return_value={"id": "test:1"})
    return db


@pytest.fixture
def log(mock_db: AsyncMock) -> ProcessingLog:
    return ProcessingLog(mock_db)


async def test_hash_input_deterministic() -> None:
    data = {"key": "value", "nested": {"a": 1}}
    h1 = ProcessingLog._hash_input(data)
    h2 = ProcessingLog._hash_input(data)
    assert h1 == h2
    assert len(h1) == 64


async def test_hash_input_order_independent() -> None:
    data1 = {"b": 2, "a": 1}
    data2 = {"a": 1, "b": 2}
    assert ProcessingLog._hash_input(data1) == ProcessingLog._hash_input(data2)


async def test_already_processed_false(log: ProcessingLog, mock_db: AsyncMock) -> None:
    mock_db.query.return_value = []
    result = await log.already_processed("stage1", {"input": "data"})
    assert result is False


async def test_already_processed_true(log: ProcessingLog, mock_db: AsyncMock) -> None:
    mock_db.query.return_value = [{"id": "log:1", "status": "completed"}]
    result = await log.already_processed("stage1", {"input": "data"})
    assert result is True


async def test_start_run(log: ProcessingLog, mock_db: AsyncMock) -> None:
    result = await log.start_run("run-1", "stage1", {"input": "data"})
    assert len(result) == 64
    mock_db.create.assert_called_once()
    call_args = mock_db.create.call_args[0]
    assert call_args[0] == "processing_log"
    assert call_args[1]["run_id"] == "run-1"
    assert call_args[1]["stage"] == "stage1"
    assert call_args[1]["status"] == "started"


async def test_complete_run(log: ProcessingLog, mock_db: AsyncMock) -> None:
    await log.complete_run("run-1", "stage1", 10, 5, ["q1", "q2"], ["src1"])
    mock_db.query.assert_called_once()


async def test_fail_run(log: ProcessingLog, mock_db: AsyncMock) -> None:
    await log.fail_run("run-1", "stage1", "something broke")
    mock_db.query.assert_called_once()


async def test_query_already_executed_false(log: ProcessingLog, mock_db: AsyncMock) -> None:
    mock_db.query.return_value = []
    result = await log.query_already_executed("test query")
    assert result is False


async def test_source_already_ingested_false(log: ProcessingLog, mock_db: AsyncMock) -> None:
    mock_db.query.return_value = []
    result = await log.source_already_ingested("https://example.com")
    assert result is False
