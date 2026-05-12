from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

class PlanningTimescale(Enum):
    FAST = auto()    # Seconds/Minutes (Oxygen, Vasopressors, Fluids)
    MID = auto()     # Hours (ICU allocation, Ventilator strategy, Staffing)
    LONG = auto()    # Days/Weeks (Discharge, Infection Control, Throughput)

@dataclass
class PlanningLayer:
    timescale: PlanningTimescale
    tick_interval: int  # How many simulation ticks per step
    horizon: int        # How many steps to plan ahead
    
    def __repr__(self):
        return f"PlanningLayer({self.timescale.name}, ticks={self.tick_interval}, horizon={self.horizon})"

class HierarchicalConfig:
    LAYERS = {
        PlanningTimescale.FAST: PlanningLayer(PlanningTimescale.FAST, tick_interval=1, horizon=10),
        PlanningTimescale.MID: PlanningLayer(PlanningTimescale.MID, tick_interval=60, horizon=12),   # 12 hours
        PlanningTimescale.LONG: PlanningLayer(PlanningTimescale.LONG, tick_interval=1440, horizon=7) # 7 days
    }
