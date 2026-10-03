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

    @property
    def duration_hours(self):
        return 0.0 if self.data.empty else float(self.data.elapsed_hours.max()-self.data.elapsed_hours.min())
    @property
    def minimum_c(self):
        return 0.0 if self.data.empty else float(self.data.temperature_c.min())
    @property
    def maximum_c(self):
        return 0.0 if self.data.empty else float(self.data.temperature_c.max())
    def export_frame(self):
        out=self.data.copy()
        out['elapsed_hours']=out['elapsed_hours']+self.offset_hours
        return out
