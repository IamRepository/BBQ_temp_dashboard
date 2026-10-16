"""Builds the small, made-up example files in tests/data. Run: python tests/make_fixtures.py

Each file reproduces one import problem found in the audit of v1.6.4 (12 October 2026),
or guards a format that already works. No real cook data is stored in the repository.
"""
from pathlib import Path

import pandas as pd

DATA = Path(__file__).parent / 'data'


def write(name, text):
    (DATA / name).write_text(text.strip() + '\n', encoding='utf-8')


def main():
    DATA.mkdir(exist_ok=True)

    # H1: year-first dates around midnight on days 1-12 (were read as 10 March / 10 April)
    write('h1_iso_midnight.csv', 'timestamp,Probe 1\n' + '\n'.join(
        f'{d} {t},{v}' for d, t, v in [
            ('2026-10-03', '23:58:00', 60.0), ('2026-10-03', '23:59:00', 60.5),
            ('2026-10-04', '00:00:00', 61.0), ('2026-10-04', '00:01:00', 61.5), ('2026-10-04', '00:02:00', 62.0)]))

    # H2: elapsed time only, in minutes and in hours (were read as nanosecond clock times)
    write('h2_elapsed_minutes.csv', 'Elapsed (min),Meat temperature\n' + '\n'.join(f'{m},{20 + m * 0.5}' for m in range(0, 121, 10)))
    write('h2_elapsed_hours.csv', 'Elapsed (h),Pit,Meat\n' + '\n'.join(f'{h / 4},{110 + h},{20 + 2 * h}' for h in range(0, 13)))

    # H3: ISO times with a UTC offset, and with Z (crashed the page)
    write('h3_utc_offset.csv', 'timestamp,Probe 1\n' + '\n'.join(f'2026-10-03T15:{m:02d}:00+02:00,{40 + m}' for m in range(0, 10)))
    write('h3_utc_z.csv', 'timestamp,Probe 1\n' + '\n'.join(f'2026-10-03T13:{m:02d}:00Z,{40 + m}' for m in range(0, 10)))

    # H4: the clock goes back during the cook (25 October 2026, 03:00 CEST -> 02:00 CET)
    rows = [('02:30:00 CEST', 80), ('02:50:00 CEST', 81), ('02:10:00 CET', 82), ('02:30:00 CET', 83), ('03:10:00 CET', 84)]
    write('h4_dst_zone_names.csv', 'timestamp,Probe 1\n' + '\n'.join(f'25/10/2026 {t},{v}' for t, v in rows))
    rows = [('02:30:00', 80), ('02:50:00', 81), ('02:10:00', 82), ('02:30:00', 83), ('03:10:00', 84)]
    write('h4_dst_no_zone.csv', 'timestamp,Probe 1\n' + '\n'.join(f'25/10/2026 {t},{v}' for t, v in rows))

    # H5: a setpoint that never changes (was dropped as "not a temperature")
    write('h5_fixed_setpoint.csv', 'timestamp,Setpoint,Probe 1\n' + '\n'.join(
        f'03/10/2026 10:{m:02d}:00,120,{20 + m}' for m in range(0, 10)))

    # M1: a column without a temperature word next to ones with it, plus non-temperature columns
    write('m1_extra_columns.csv', 'Time,Pit temp,Meat,Target,Fan %,Battery\n' + '\n'.join(
        f'03/10/2026 10:{m:02d}:00,{110 + m},{20 + m},{120 + m % 3},{40 + m},{95 - m}' for m in range(0, 10)))

    # M8: Fahrenheit
    write('m8_fahrenheit.csv', 'Time,Meat (°F),Pit (°F)\n' + '\n'.join(
        f'03/10/2026 10:{m:02d}:00,{150 + m},{250 + m}' for m in range(0, 5)))

    # Guards for formats that already work and must keep working
    write('ok_device_cest.csv', 'timestamp, cavity temperature, Probe 1, Probe 2\n' + '\n'.join(
        [f'03/10/2026 15:34:{s:02d} CEST, {31.2 - s / 10:.3f}, {18.7 - s / 100:.3f}' for s in range(0, 5)]
        + [f'03/10/2026 15:34:{s:02d} CEST, {30.7 - s / 10:.3f}, {18.6 - s / 100:.3f}, {20.7 - s / 10:.3f}' for s in range(5, 12)]
        + ['03/10/2026 15:34:12 CEST, 29.5']))
    write('ok_semicolon_comma.csv', 'Zeit;Kerntemperatur\n03.10.2026 10:00:00;23,5\n03.10.2026 10:01:00;24,0\n03.10.2026 10:02:00;24,5')

    with pd.ExcelWriter(DATA / 'ok_two_sheets.xlsx', engine='openpyxl') as writer:
        pd.DataFrame({'Timestamp': pd.date_range('2026-10-03 10:00', periods=5, freq='min'), 'Meat': [20, 21, 22, 23, 24]}).to_excel(writer, sheet_name='Cook 1', index=False)
        pd.DataFrame({'Timestamp': pd.date_range('2026-10-04 10:00', periods=5, freq='min'), 'Meat': [30, 31, 32, 33, 34]}).to_excel(writer, sheet_name='Cook 2', index=False)

    # L2: the dashboard's own Excel export, imported again (one sheet, "(°C)" in the column names)
    with pd.ExcelWriter(DATA / 'l2_dashboard_export.xlsx', engine='openpyxl') as writer:
        pd.DataFrame({'Timestamp': pd.date_range('2026-10-03 15:34', periods=5, freq='min'),
                      'Connet - Probe 1 (°C)': [23.5, 30.1, 40.2, 50.3, 60.4],
                      'Smoque_XL - Probe 2 (°C)': [18.7, 19.0, 19.5, 20.1, 20.8]}).to_excel(writer, sheet_name='Cook profiles', index=False)

    # v1.7.0: two Typhur probes as BBQ Chart to Data writes them (UTF-8 with BOM, day-first Timestamp,
    # Ambient + Meat), started 30 min apart; one start read from a screenshot, the other typed.
    for number, start, source in ((1, 10 * 60, 'read and confirmed'), (2, 10 * 60 + 30, 'typed')):
        rows = [f'16/10/2026 {(start + m) // 60:02d}:{(start + m) % 60:02d},{110 + m % 7},{20 + m * 0.4:.1f},{source}' for m in range(0, 120, 5)]
        body = 'Timestamp,Ambient temperature (°C),Meat temperature (°C),Start time source\n' + '\n'.join(rows) + '\n'
        (DATA / f'c2d_typhur_probe_{number}.csv').write_bytes(b'\xef\xbb\xbf' + body.encode('utf-8'))

        # H2 guard: Excel date serial numbers under a Date header are clock times, not elapsed values
    serial = [46298 + (10 * 60 + m) / 1440 for m in range(0, 5)]  # 3 October 2026, 10:00 to 10:04
    with pd.ExcelWriter(DATA / 'ok_excel_serial_dates.xlsx', engine='openpyxl') as writer:
        pd.DataFrame({'Date': serial, 'Meat': [20, 21, 22, 23, 24]}).to_excel(writer, index=False)


if __name__ == '__main__':
    main()
