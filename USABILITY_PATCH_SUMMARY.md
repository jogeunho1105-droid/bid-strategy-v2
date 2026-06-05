# bid-strategy-v2 usability patch

## Changed files

- `app.py`
- `modules/bid_strategy_legacy.py`
- `modules/excel_exporter.py`
- `README.md`

## User-facing improvements

- Added a top-level strategy summary after bid-list upload.
- Added counts for total targets, normal rows, rows needing review, and 3-point strategy rows.
- Added a prioritized bid table sorted by a practical review score.
- Added a `확인필요` column with review reasons such as missing base amount, weak data, grade D, missing recommended range, or dispersed predictions.
- Replaced rendering all bid detail expanders with a single selected-bid detail view for faster use with many rows.
- Added clearer warnings when both pattern statistics and uploaded history are unavailable.
- Added data-management notice about Streamlit Cloud local file persistence.

## Data/model fixes

- `load_pattern_stats()` now checks both `data/pattern_stats.json` and root `pattern_stats.json`.
- `load_pattern_stats()` now unwraps `{"orgs": {...}}` pattern-stat files automatically.

## Excel output improvements

- Added `피드백입력` sheet to the strategy workbook.
- Feedback sheet includes bid id, bid number, recommended range, A/B/C points, adopted strategy, actual rate, win/loss, and notes.

## Verification

- Local Python compile check passed for:
  - `app.py`
  - `modules/bid_strategy_legacy.py`
  - `modules/excel_exporter.py`

## GitHub status

Direct GitHub update failed because the connected GitHub integration does not currently have write access to `jogeunho1105-droid/bid-strategy-v2`.

Error:

```text
403 Resource not accessible by integration
```

The ready-to-upload bundle is:

```text
C:\Users\USER\Documents\Codex\2026-06-01\new-chat-2\bid-strategy-v2-usability-patch.zip
```
