from dataclasses import dataclass, field
import numpy as np
import pandas as pd


@dataclass
class CookProfile:
    profile_id: str
    name: str
    source_file: str
    channel: str
    color: str
    data: pd.DataFrame
    visible: bool = True
    offset_hours: float = 0.0
    metadata: dict = field(default_factory=dict)
    trim_start: int = 0
    trim_end: int | None = None
    is_setpoint: bool = False  # a target the cooker was set to hold, drawn dashed and never smoothed

    def trim_bounds(self):
        count = len(self.data)
        if count == 0:
            return 0, 0
        start = max(0, min(int(self.trim_start), count - 1))
        end_value = count - 1 if self.trim_end is None else int(self.trim_end)
        end = max(start, min(end_value, count - 1))
        return start, end

    @property
    def plotted_data(self):
        if self.data.empty:
            return self.data.copy()
        start, end = self.trim_bounds()
        return self.data.iloc[start:end + 1].copy().reset_index(drop=True)

    @property
    def duration_hours(self):
        frame = self.plotted_data
        return 0.0 if frame.empty else float(frame.elapsed_hours.max() - frame.elapsed_hours.min())

    @property
    def minimum_c(self):
        frame = self.plotted_data
        return 0.0 if frame.empty else float(frame.temperature_c.min())

    @property
    def maximum_c(self):
        frame = self.plotted_data
        return 0.0 if frame.empty else float(frame.temperature_c.max())

    def export_frame(self):
        # The visible data window with the time offset applied to both time columns, as in the charts and export.
        out = self.plotted_data
        out['elapsed_hours'] = out['elapsed_hours'] + self.offset_hours
        if 'timestamp' in out:
            out['timestamp'] = out['timestamp'] + pd.to_timedelta(self.offset_hours, unit='h')
        return out

    def time_axis(self, clock):
        """Each reading's time as drawn: clock time with the offset, or hours on the Start timeline (with the offset)."""
        if clock and 'timestamp' in self.data:
            return self.data.timestamp + pd.to_timedelta(self.offset_hours, unit='h')
        return self.data.elapsed_hours + self.offset_hours

    def window(self, clock):
        """(first, last) time of the visible data window, on the same axis as time_axis."""
        times = self.time_axis(clock).reset_index(drop=True)
        start, end = self.trim_bounds()
        return times.iloc[start], times.iloc[end]

    def trim_to(self, start, end, clock):
        """Show only the readings between start and end. Returns False, and changes nothing, when no reading is inside."""
        times = self.time_axis(clock).to_numpy()
        if clock:
            start, end = pd.Timestamp(start).to_datetime64(), pd.Timestamp(end).to_datetime64()
        inside = np.flatnonzero((times >= start) & (times <= end))
        if not len(inside):
            return False
        self.trim_start, self.trim_end = int(inside[0]), int(inside[-1])
        return True
