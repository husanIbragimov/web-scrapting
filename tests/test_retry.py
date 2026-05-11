import pytest
from utils.retry import async_retry

@pytest.mark.asyncio
async def test_succeeds_on_first_try():
    calls = []
    async def fn():
        calls.append(1)
        return "ok"
    result = await async_retry(fn, retries=3, backoff_base=0.01)
    assert result == "ok"
    assert len(calls) == 1

@pytest.mark.asyncio
async def test_retries_on_exception_and_succeeds():
    calls = []
    async def fn():
        calls.append(1)
        if len(calls) < 3:
            raise ValueError("boom")
        return "ok"
    result = await async_retry(fn, retries=3, backoff_base=0.01)
    assert result == "ok"
    assert len(calls) == 3

@pytest.mark.asyncio
async def test_returns_none_after_all_retries_exhausted():
    async def fn():
        raise RuntimeError("always fails")
    result = await async_retry(fn, retries=3, backoff_base=0.01)
    assert result is None
