"""Tests for tgops.utils.rate_limiter."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from tgops.utils.rate_limiter import BATCH_SIZE, batch_delay, emergency_delay, human_delay


class TestHumanDelay:
    @pytest.mark.asyncio
    async def test_stays_within_bounds_default(self):
        """human_delay with default base stays in [0.5, base*3] range."""
        base = 2.5
        min_val = 0.5
        max_val = base * 3  # 7.5

        actual_sleeps = []

        async def fake_sleep(seconds):
            actual_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            # Run many times to check distribution
            for _ in range(50):
                await human_delay(base)

        for s in actual_sleeps:
            assert s >= min_val, f"Delay {s} is below floor {min_val}"
            assert s <= max_val, f"Delay {s} exceeds ceiling {max_val}"

    @pytest.mark.asyncio
    async def test_stays_within_bounds_small_base(self):
        """human_delay with small base is clamped to at least 0.5s."""
        base = 0.01
        actual_sleeps = []

        async def fake_sleep(seconds):
            actual_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            for _ in range(20):
                await human_delay(base)

        for s in actual_sleeps:
            assert s >= 0.5, f"Delay {s} is below floor 0.5"

    @pytest.mark.asyncio
    async def test_calls_asyncio_sleep(self):
        """human_delay actually calls asyncio.sleep exactly once."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await human_delay(1.0)
            mock_sleep.assert_called_once()
            call_arg = mock_sleep.call_args[0][0]
            assert 0.5 <= call_arg <= 3.0


class TestEmergencyDelay:
    @pytest.mark.asyncio
    async def test_stays_within_bounds_default(self):
        """emergency_delay with default base stays at or above 0.2s."""
        base = 0.4
        min_val = 0.2

        actual_sleeps = []

        async def fake_sleep(seconds):
            actual_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            for _ in range(50):
                await emergency_delay(base)

        for s in actual_sleeps:
            assert s >= min_val, f"Delay {s} is below floor {min_val}"

    @pytest.mark.asyncio
    async def test_stays_near_base(self):
        """emergency_delay stays within base ± 0.15 (before floor clamp)."""
        base = 1.0
        actual_sleeps = []

        async def fake_sleep(seconds):
            actual_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            for _ in range(50):
                await emergency_delay(base)

        for s in actual_sleeps:
            # After clamping to 0.5, values should be in [0.5, 1.15]
            assert s >= 0.5
            assert s <= 1.15 + 1e-9  # base + 0.15 = 1.15

    @pytest.mark.asyncio
    async def test_calls_asyncio_sleep(self):
        """emergency_delay calls asyncio.sleep once."""
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await emergency_delay(0.4)
            mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    async def test_minimum_floor_with_zero_base(self):
        """emergency_delay is always at least 0.2 even with base=0."""
        actual_sleeps = []

        async def fake_sleep(seconds):
            actual_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            for _ in range(20):
                await emergency_delay(0.0)

        for s in actual_sleeps:
            assert s >= 0.2


class TestBatchDelay:
    def test_batch_size_is_20(self):
        """BATCH_SIZE constant is 20."""
        assert BATCH_SIZE == 20

    @pytest.mark.asyncio
    async def test_batch_delay_calls_sleep(self):
        """batch_delay calls asyncio.sleep with a value in [30, 60]."""
        actual_sleeps = []

        async def fake_sleep(seconds):
            actual_sleeps.append(seconds)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            await batch_delay()

        assert len(actual_sleeps) == 1
        assert 30 <= actual_sleeps[0] <= 60
