import pandas as pd
from pathlib import Path
from pandas.tseries.offsets import CustomBusinessDay


def load_and_clean_csv(csv_path: Path) -> pd.DataFrame:
    """Load raw CSV and normalize column names for OHLCV processing."""
    df = pd.read_csv(csv_path)
    if 'date' not in df.columns:
        raise ValueError(f"Expected 'date' column in {csv_path}, got: {list(df.columns)}")

    df = df.rename(
        columns={
            'date': 'Datetime',
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        }
    )
    df['Datetime'] = pd.to_datetime(df['Datetime'])
    df['date'] = df['Datetime'].dt.date
    return df


def find_longest_continuous_trading_period(df: pd.DataFrame) -> tuple[Path, pd.Timestamp, pd.Timestamp, int]:
    """Return the start, end, and length of the longest continuous trading-day block."""
    trade_days = sorted(df['date'].unique())
    if not trade_days:
        raise ValueError('No trading days found in the dataset.')

    business_day = CustomBusinessDay(weekmask='Mon Tue Wed Thu Fri')
    best = {'start': trade_days[0], 'end': trade_days[0], 'trading_days': 1}
    cur_start = trade_days[0]
    cur_prev = trade_days[0]

    for current in trade_days[1:]:
        expected_next = (pd.Timestamp(cur_prev) + business_day).date()
        if current == expected_next:
            cur_prev = current
        else:
            current_length = len([d for d in trade_days if d >= cur_start and d <= cur_prev])
            if current_length > best['trading_days']:
                best.update({'start': cur_start, 'end': cur_prev, 'trading_days': current_length})
            cur_start = current
            cur_prev = current

    current_length = len([d for d in trade_days if d >= cur_start and d <= cur_prev])
    if current_length > best['trading_days']:
        best.update({'start': cur_start, 'end': cur_prev, 'trading_days': current_length})

    return best['start'], best['end'], best['trading_days']


def save_longest_segment(df: pd.DataFrame, start_date, end_date, out_path: Path) -> pd.DataFrame:
    segment = df[(df['date'] >= start_date) & (df['date'] <= end_date)].copy()
    segment = segment.sort_values('Datetime').reset_index(drop=True)
    segment.to_csv(out_path, index=False)
    return segment


def main() -> None:
    repo_root = Path(__file__).parent
    source_csv = repo_root / 'NIFTY 50_5minute.csv'
    out_dir = repo_root / 'data'
    out_dir.mkdir(exist_ok=True)
    cleaned_csv = out_dir / 'NIFTY_50_5minute_cleaned.csv'
    longest_csv = out_dir / 'NIFTY_50_5minute_longest_continuous.csv'

    print(f'Loading raw file: {source_csv}')
    df = load_and_clean_csv(source_csv)

    print('Saving cleaned OHLCV dataset...')
    df.to_csv(cleaned_csv, index=False)

    print('Computing longest continuous trading-day block...')
    start_date, end_date, length = find_longest_continuous_trading_period(df)
    print(f'Longest continuous period: {start_date} to {end_date} ({length} trading days)')

    print(f'Saving longest continuous block to: {longest_csv}')
    segment = save_longest_segment(df, start_date, end_date, longest_csv)
    print(f'Longest segment rows: {len(segment)}')
    print('Done.')


if __name__ == '__main__':
    main()
