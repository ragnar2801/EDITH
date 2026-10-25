"""Refresh: idempotent upserts, renames, closures and the safety check (D-038, D-041)."""

from decimal import Decimal

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from friday.core.db import session_scope
from friday.core.instruments.models import Instrument, InstrumentAlias, InstrumentImport
from friday.core.instruments.service import effective_classification, set_override


def instrument(factory, **where) -> Instrument:
    with session_scope(factory) as session:
        statement = (
            select(Instrument)
            .filter_by(**where)
            .options(selectinload(Instrument.aliases), selectinload(Instrument.override))
        )
        found = session.scalars(statement).all()
        assert len(found) == 1, f"{len(found)} instruments match {where}"
        return found[0]


def snapshot(factory) -> list[tuple]:
    with session_scope(factory) as session:
        rows = session.execute(text("SELECT * FROM instruments ORDER BY id")).all()
        aliases = session.execute(text("SELECT * FROM instrument_aliases ORDER BY id")).all()
        index = session.execute(text("SELECT rowid, * FROM instrument_search ORDER BY rowid")).all()
    return [tuple(row) for row in [*rows, *aliases, *index]]


def test_first_refresh_imports_every_list(refresh, factory) -> None:
    results = refresh()

    assert {source: result.status for source, result in results.items()} == {
        "nse": "ok",
        "amfi": "ok",
        "us": "ok",
    }
    assert results["nse"].added == 12  # 7 stocks + 5 ETFs
    assert results["us"].added == 9  # warrant, preferred and test issues left out
    infy = instrument(factory, exchange="NSE", symbol="INFY")
    assert (infy.kind, infy.currency, infy.market, infy.is_active) == ("stock", "INR", "IN", True)
    assert instrument(factory, exchange="NYSE", symbol="INFY").currency == "USD"
    assert instrument(factory, symbol="AAPL").cik == "0000320193"


def test_second_refresh_changes_nothing(refresh, factory) -> None:
    refresh()
    before = snapshot(factory)

    results = refresh()

    for result in results.values():
        assert (result.added, result.updated, result.deactivated, result.reactivated) == (
            0,
            0,
            0,
            0,
        )
        assert result.aliases_added == 0
    assert snapshot(factory) == before  # not even an updated_at moved


def test_each_run_is_logged(refresh, factory) -> None:
    refresh()
    refresh("nse")

    with session_scope(factory) as session:
        runs = session.scalars(select(InstrumentImport).order_by(InstrumentImport.id)).all()
        assert [(run.source, run.status) for run in runs] == [
            ("nse", "ok"),
            ("amfi", "ok"),
            ("us", "ok"),
            ("nse", "ok"),
        ]
        assert runs[0].added == 12 and runs[3].added == 0


def test_an_nse_etf_and_its_amfi_scheme_are_one_instrument(refresh, factory) -> None:
    refresh()

    etf = instrument(factory, symbol="NIFTYBEES")
    assert etf.amfi_code == "140084"
    assert etf.name == "Nippon India ETF Nifty 50 BeES"  # AMFI's readable name
    assert etf.fund_house == "Nippon India Mutual Fund"
    assert (etf.source, etf.kind, etf.exchange) == ("nse", "etf", "NSE")
    with session_scope(factory) as session:
        assert session.scalars(select(Instrument).filter_by(amfi_code="140084")).one().id == etf.id


def test_old_symbols_and_names_become_aliases(refresh, factory) -> None:
    refresh()

    eternal = instrument(factory, symbol="ETERNAL")
    aliases = {(alias.kind, alias.value) for alias in eternal.aliases}
    assert ("symbol", "ZOMATO") in aliases
    assert ("name", "Zomato Limited") in aliases


def test_a_symbol_change_keeps_the_instrument(refresh, factory, edit_list) -> None:
    refresh()
    old = instrument(factory, symbol="M&M")

    # Same company, same ISIN, new symbol.
    edit_list("EQUITY_L.csv", "M&M,Mahindra", "MAHINDRA,Mahindra")
    result = refresh("nse")["nse"]

    renamed = instrument(factory, symbol="MAHINDRA")
    assert renamed.id == old.id
    assert ("symbol", "M&M") in {(a.kind, a.value) for a in renamed.aliases}
    assert (result.added, result.updated, result.deactivated) == (0, 1, 0)


def test_a_symbol_and_isin_change_follows_nse_symbol_changes(refresh, factory, edit_list) -> None:
    refresh()
    old = instrument(factory, symbol="20MICRONS")

    edit_list(
        "EQUITY_L.csv",
        "20MICRONS,20 Microns Limited,EQ,06-OCT-2008,5,1,INE144J01027",
        "TWENTYMIC,Twenty Microns Limited,EQ,06-OCT-2008,5,1,INE999Z01011",
    )
    edit_list(
        "symbolchange.csv",
        "ETERNAL LIMITED,ZOMATO",
        "Twenty Microns Limited,20MICRONS,TWENTYMIC,01-OCT-2026\nETERNAL LIMITED,ZOMATO",
    )
    refresh("nse")

    renamed = instrument(factory, symbol="TWENTYMIC")
    assert renamed.id == old.id
    assert renamed.isin == "INE999Z01011"
    assert {("symbol", "20MICRONS"), ("name", "20 Microns Limited")} <= {
        (a.kind, a.value) for a in renamed.aliases
    }


def test_a_face_value_split_changes_the_isin_but_not_the_instrument(
    refresh, factory, edit_list
) -> None:
    refresh()
    old = instrument(factory, symbol="IRCTC")

    edit_list("EQUITY_L.csv", "INE335Y01020", "INE335Y01038")  # same issuer, new security
    result = refresh("nse")["nse"]

    after = instrument(factory, symbol="IRCTC")
    assert after.id == old.id and after.isin == "INE335Y01038"
    assert (result.added, result.updated) == (0, 1)


def test_a_reused_symbol_is_a_new_instrument(refresh, factory, edit_list) -> None:
    refresh()
    old = instrument(factory, symbol="20MICRONS")

    # The old company delists and a different one (different issuer code) takes the symbol.
    edit_list(
        "EQUITY_L.csv",
        "20 Microns Limited,EQ,06-OCT-2008,5,1,INE144J01027",
        "Twenty New Limited,EQ,01-OCT-2026,1,1,INE0AB101015",
    )
    result = refresh("nse")["nse"]

    with session_scope(factory) as session:
        rows = session.scalars(select(Instrument).filter_by(symbol="20MICRONS")).all()
        states = sorted((row.id == old.id, row.is_active) for row in rows)
    assert states == [(False, True), (True, False)]  # old row kept but inactive
    assert (result.added, result.deactivated) == (1, 1)


def test_delisted_instruments_become_inactive_and_come_back(refresh, factory, edit_list) -> None:
    refresh()
    hdfc = instrument(factory, symbol="HDFCBANK")
    line = "HDFCBANK,HDFC Bank Limited,EQ,08-NOV-1995,1,1,INE040A01034,1\n"

    edit_list("EQUITY_L.csv", line, "")
    assert refresh("nse")["nse"].deactivated == 1
    assert not instrument(factory, id=hdfc.id).is_active

    edit_list("EQUITY_L.csv", "INFY,", line + "INFY,")
    assert refresh("nse")["nse"].reactivated == 1
    assert instrument(factory, id=hdfc.id).is_active


def test_closed_schemes_are_imported_inactive(refresh, factory) -> None:
    refresh()

    assert not instrument(factory, amfi_code="142916").is_active
    assert instrument(factory, amfi_code="122639").is_active


def test_a_much_shorter_list_is_rejected(refresh, factory, lists) -> None:
    refresh()
    text_ = (lists / "EQUITY_L.csv").read_text(encoding="utf-8")
    header, *rows = text_.splitlines()
    (lists / "EQUITY_L.csv").write_text("\n".join([header, rows[0]]), encoding="utf-8")
    (lists / "eq_etfseclist.csv").write_text(
        (lists / "eq_etfseclist.csv").read_text(encoding="utf-8").splitlines()[0],
        encoding="utf-8",
    )

    result = refresh("nse")["nse"]

    assert result.status == "failed"
    assert "refusing to deactivate" in (result.message or "")
    assert instrument(factory, symbol="HDFCBANK").is_active  # nothing was changed


def test_a_failing_source_doesnt_stop_the_others(refresh, factory, lists) -> None:
    (lists / "NAVAll.txt").write_text("<html><body>Object Moved</body></html>", encoding="utf-8")

    results = refresh()

    assert results["amfi"].status == "failed"
    assert "doesn't look right" in (results["amfi"].message or "")
    assert results["nse"].status == results["us"].status == "ok"


def test_missing_change_files_are_only_a_warning(refresh, lists) -> None:
    (lists / "symbolchange.csv").unlink()

    result = refresh("nse")["nse"]

    assert result.status == "ok"
    assert any("symbolchange.csv" in warning for warning in result.warnings)


def test_every_active_fund_in_the_scheme_master_has_a_plan_and_option(refresh, factory) -> None:
    result = refresh("amfi")["amfi"]

    assert result.warnings == []
    with session_scope(factory) as session:
        unlabelled = session.scalars(
            select(Instrument.amfi_code).where(
                Instrument.kind == "mutual_fund",
                Instrument.is_active,
                (Instrument.plan.is_(None)) | (Instrument.option_kind.is_(None)),
            )
        ).all()
    assert unlabelled == []
    assert (
        instrument(factory, amfi_code="127044").option,
        instrument(factory, amfi_code="127044").plan,
    ) == ("IDCW", "direct")


def test_without_the_scheme_master_plan_and_option_are_kept(refresh, factory, lists) -> None:
    refresh("amfi")
    (lists / "SchemeData.csv").unlink()

    result = refresh("amfi")["amfi"]

    assert result.status == "ok"
    assert any("SchemeData.csv" in warning for warning in result.warnings)
    assert result.updated == 0
    assert instrument(factory, amfi_code="127042").option == "Growth"


def test_a_us_ticker_change_is_matched_by_cik(refresh, factory, edit_list) -> None:
    refresh()
    old = instrument(factory, symbol="GOOGL")

    edit_list("nasdaqlisted.txt", "GOOGL|Alphabet", "GOOGX|Alphabet")
    edit_list("company_tickers_exchange.json", '"GOOGL"', '"GOOGX"')
    refresh("us")

    renamed = instrument(factory, symbol="GOOGX")
    assert renamed.id == old.id
    assert ("symbol", "GOOGL") in {(a.kind, a.value) for a in renamed.aliases}


def test_my_override_survives_refresh(refresh, factory) -> None:
    refresh()
    fund = instrument(factory, amfi_code="122639")
    with session_scope(factory) as session:
        set_override(
            session,
            session.get(Instrument, fund.id),
            {"equity": Decimal(65), "debt": Decimal(35)},
            "GLOBAL",
        )

    refresh()

    after = instrument(factory, id=fund.id)
    assert after.allocation() == {"equity": Decimal(100)}  # the rule, still refreshed
    effective = effective_classification(after)
    assert (effective.asset_class, effective.exposure) == ("hybrid", "GLOBAL")


def test_alias_rows_are_unique(refresh, factory) -> None:
    refresh()
    refresh()

    with session_scope(factory) as session:
        values = [
            (a.instrument_id, a.kind, a.value) for a in session.scalars(select(InstrumentAlias))
        ]
    assert len(values) == len(set(values))
