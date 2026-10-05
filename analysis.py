"""Smoothing and setpoint-versus-probe comparison."""
import numpy as np
import pandas as pd

EPOCH = pd.Timestamp('1970-01-01')
MAX_SAMPLE_WEIGHT_H = 30 / 3600  # a gap between two samples never counts as more than 30 s


def smooth(frame, minutes):
    """Centred rolling mean over a time window (e.g. 5 minutes), whatever the number of samples in it."""
    values = frame.temperature_c
    if not minutes or frame.empty:
        return values
    index = pd.to_datetime(frame.elapsed_hours.to_numpy() * 3600, unit='s')
    rolled = pd.Series(values.to_numpy(), index=index).rolling(f'{int(round(minutes * 60))}s', center=True, min_periods=1).mean()
    return pd.Series(rolled.to_numpy(), index=frame.index)


def _hours(profile, frame):
    """Absolute time in hours, shifted by the profile's offset, so separate files line up."""
    if 'timestamp' in frame:
        base = (frame.timestamp - EPOCH).dt.total_seconds().to_numpy() / 3600
    else:
        base = frame.elapsed_hours.to_numpy()
    return base + profile.offset_hours


def compare(setpoint, probe, band_c=10.0, smoothing_minutes=0, skip_minutes=0):
    """Compare a probe with a setpoint profile.

    Samples are matched by clock time (or by elapsed time if neither file has timestamps),
    using the trimmed data window of both profiles. The setpoint is interpolated to each
    probe sample. Differences are probe minus setpoint.
    Returns (result, problem); exactly one of them is None.
    """
    sp, pr = setpoint.plotted_data, probe.plotted_data
    if sp.empty or pr.empty:
        return None, 'One of the profiles has no data in its visible window.'
    if ('timestamp' in sp) != ('timestamp' in pr):
        return None, 'One profile has timestamps and the other does not, so they cannot be matched in time.'

    t_sp, t_pr = _hours(setpoint, sp), _hours(probe, pr)
    y_sp = sp.temperature_c.to_numpy()
    y_pr = smooth(pr, smoothing_minutes).to_numpy()

    start = max(t_sp.min(), t_pr.min()) + skip_minutes / 60
    end = min(t_sp.max(), t_pr.max())
    keep = (t_pr >= start) & (t_pr <= end)
    if keep.sum() < 2:
        return None, 'The two profiles do not overlap in time (after the warm-up skip). Check the time offsets and trimmed windows.'

    t, measured = t_pr[keep], y_pr[keep]
    target = np.interp(t, t_sp, y_sp)
    diff = measured - target
    # Each sample represents half of the interval on either side of it; long data gaps are capped.
    gaps = np.minimum(np.diff(t), MAX_SAMPLE_WEIGHT_H)
    weight = np.zeros(len(t))
    weight[:-1] += gaps / 2
    weight[1:] += gaps / 2
    total = weight.sum()
    inside = np.abs(diff) <= band_c

    x = (EPOCH + pd.to_timedelta(t, unit='h')) if 'timestamp' in pr else t
    return {
        'mean_diff': float((diff * weight).sum() / total),
        'min_diff': float(diff.min()),
        'max_diff': float(diff.max()),
        'within_share': float((weight * inside).sum() / total),
        'minutes': float(total * 60),
        'band_c': float(band_c),
        'frame': pd.DataFrame({'x': x, 'probe_c': measured, 'setpoint_c': target, 'difference_c': diff}),
        'uses_clock_time': 'timestamp' in pr,
    }, None
