"""Unit tests for the pure MRL engine core -- no database required."""

from datetime import datetime, timedelta, timezone

from app.models.enums import ProductionStatus, SaleProduct, Species, Tissue
from app.services.mrl_engine import (
    SaleVerdict,
    applicable_tissues,
    build_withdrawal_rows,
    evaluate_sale,
    summarize_windows,
    withdrawal_clears_at,
)
from app.utils.timeutil import as_ist, ensure_aware

UTC = timezone.utc


class _Rule:
    def __init__(self, milk=None, meat=None, eggs=None):
        self.withdrawal_milk_days = milk
        self.withdrawal_meat_days = meat
        self.withdrawal_eggs_days = eggs


def _w(tissue, starts, clears, adm=1, drug="TestDrug"):
    from app.services.mrl_engine import WindowInfo

    return WindowInfo(tissue=tissue, starts_at=starts, clears_at=clears,
                      administration_id=adm, drug_name=drug)


# --------------------------------------------------------------------------- #
# applicable tissues
# --------------------------------------------------------------------------- #

def test_lactating_cow_gets_milk_and_meat():
    assert set(applicable_tissues(Species.cattle, ProductionStatus.lactating)) == {
        Tissue.milk, Tissue.meat
    }


def test_dry_cow_gets_only_meat():
    assert applicable_tissues(Species.cattle, ProductionStatus.dry) == [Tissue.meat]


def test_laying_hen_gets_eggs_and_meat():
    assert set(applicable_tissues(Species.poultry, ProductionStatus.laying)) == {
        Tissue.eggs, Tissue.meat
    }


def test_lactating_poultry_is_not_a_thing():
    # poultry never produces milk even with a nonsense production status
    assert Tissue.milk not in applicable_tissues(Species.poultry, ProductionStatus.lactating)


# --------------------------------------------------------------------------- #
# withdrawal window construction
# --------------------------------------------------------------------------- #

def test_clears_at_is_end_of_nth_ist_day():
    # last dose 2026-08-10 14:00 IST, 3-day WP -> clears end of 2026-08-13 IST
    last_dose = datetime(2026, 8, 10, 14, 0, tzinfo=UTC)  # 19:30 IST
    clears = withdrawal_clears_at(last_dose, 3.0)
    assert as_ist(clears).date() == datetime(2026, 8, 13).date()
    assert as_ist(clears).hour == 23 and as_ist(clears).minute == 59


def test_fractional_wp_rounds_up_safe_side():
    last_dose = datetime(2026, 8, 10, 4, 0, tzinfo=UTC)
    assert withdrawal_clears_at(last_dose, 0.5) == withdrawal_clears_at(last_dose, 1.0)


def test_build_rows_skips_null_tissues():
    started = datetime(2026, 8, 10, tzinfo=UTC)
    last_dose = started  # single-dose course
    rows = build_withdrawal_rows(
        Species.cattle, ProductionStatus.lactating, started, last_dose, _Rule(milk=None, meat=5)
    )
    assert [r.tissue for r in rows] == [Tissue.meat]


def test_build_rows_for_lactating_cow():
    started = datetime(2026, 8, 10, tzinfo=UTC)
    last_dose = started + timedelta(days=2)  # 3-day course
    rows = build_withdrawal_rows(
        Species.cattle, ProductionStatus.lactating, started, last_dose, _Rule(milk=3, meat=5)
    )
    tissues = {r.tissue for r in rows}
    assert tissues == {Tissue.milk, Tissue.meat}
    meat_row = next(r for r in rows if r.tissue == Tissue.meat)
    milk_row = next(r for r in rows if r.tissue == Tissue.milk)
    assert meat_row.clears_at > milk_row.clears_at  # 5d vs 3d after last dose
    assert meat_row.starts_at == started  # unsafe from the FIRST dose
    tissues = {r.tissue for r in rows}
    assert tissues == {Tissue.milk, Tissue.meat}
    meat_row = next(r for r in rows if r.tissue == Tissue.meat)
    milk_row = next(r for r in rows if r.tissue == Tissue.milk)
    assert meat_row.clears_at > milk_row.clears_at  # 5d vs 3d


# --------------------------------------------------------------------------- #
# snapshot / summarization
# --------------------------------------------------------------------------- #

def test_overlapping_drugs_collapse_to_longest_clock():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    windows = [
        _w(Tissue.milk, now - timedelta(days=1), now + timedelta(days=1), adm=1, drug="A"),
        _w(Tissue.milk, now - timedelta(days=2), now + timedelta(days=5), adm=2, drug="B"),
        _w(Tissue.meat, now - timedelta(days=1), now + timedelta(days=2), adm=1, drug="A"),
    ]
    status = summarize_windows(windows, now)
    assert status.overall == "WITHDRAWAL_ACTIVE"
    milk = next(t for t in status.tissues if t["tissue"] == "milk")
    assert milk["clears_at"] == now + timedelta(days=5)
    assert milk["drug_name"] == "B"
    assert len(status.tissues) == 2


def test_expired_windows_are_ignored():
    now = datetime(2026, 8, 20, tzinfo=UTC)
    windows = [_w(Tissue.meat, now - timedelta(days=10), now - timedelta(days=5))]
    status = summarize_windows(windows, now)
    assert status.overall == "CLEAR"
    assert status.tissues == []


def test_clear_today_band():
    now = datetime(2026, 8, 20, 10, 0, tzinfo=UTC)
    windows = [_w(Tissue.milk, now - timedelta(hours=10), now + timedelta(hours=8))]
    assert summarize_windows(windows, now).overall == "CLEAR_TODAY"


# --------------------------------------------------------------------------- #
# sale evaluation
# --------------------------------------------------------------------------- #

def test_sale_inside_window_is_violation():
    now = datetime(2026, 8, 20, tzinfo=UTC)
    windows = [_w(Tissue.milk, now - timedelta(days=1), now + timedelta(days=3))]
    verdict = evaluate_sale(SaleProduct.milk, windows, now)
    assert verdict.is_violation
    assert verdict.hours_premature > 70  # ~3 days
    assert verdict.linked_administration_ids == [1]


def test_sale_after_clearance_is_clean():
    now = datetime(2026, 8, 20, tzinfo=UTC)
    windows = [_w(Tissue.milk, now - timedelta(days=5), now - timedelta(days=2))]
    verdict = evaluate_sale(SaleProduct.milk, windows, now)
    assert not verdict.is_violation
    assert not verdict.near_miss


def test_sale_within_24h_after_clearance_is_near_miss():
    clear = datetime(2026, 8, 20, 12, 0, tzinfo=UTC)
    windows = [_w(Tissue.milk, clear - timedelta(days=4), clear)]
    verdict = evaluate_sale(SaleProduct.milk, windows, clear + timedelta(hours=6))
    assert not verdict.is_violation
    assert verdict.near_miss


def test_meat_sale_checked_against_meat_not_milk_window():
    now = datetime(2026, 8, 20, tzinfo=UTC)
    windows = [
        _w(Tissue.milk, now - timedelta(days=1), now + timedelta(days=3)),
        _w(Tissue.meat, now - timedelta(days=5), now - timedelta(days=1)),
    ]
    verdict = evaluate_sale(SaleProduct.meat, windows, now)
    assert not verdict.is_violation


def test_live_animal_sale_uses_meat_window():
    now = datetime(2026, 8, 20, tzinfo=UTC)
    windows = [_w(Tissue.meat, now - timedelta(days=1), now + timedelta(days=10))]
    verdict = evaluate_sale(SaleProduct.live_animal, windows, now)
    assert verdict.is_violation


def test_egg_sale_uses_egg_window():
    now = datetime(2026, 8, 20, tzinfo=UTC)
    windows = [_w(Tissue.eggs, now - timedelta(days=1), now + timedelta(days=2))]
    assert evaluate_sale(SaleProduct.eggs, windows, now).is_violation
