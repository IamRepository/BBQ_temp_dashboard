from dataclasses import dataclass, field
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
        out = self.plotted_data
        out['elapsed_hours'] = out['elapsed_hours'] + self.offset_hours
        return out
