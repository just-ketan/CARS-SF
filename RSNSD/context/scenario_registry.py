"""
Scenario Registry

Central registry for all supported rural operating scenarios.
"""

from .scenarios.normal_day import NORMAL_DAY
from .scenarios.school_hours import SCHOOL_HOURS
from .scenarios.harvest import HARVEST
from .scenarios.market_day import MARKET_DAY
from .scenarios.festival import FESTIVAL
from .scenarios.rainfall import RAINFALL
from .scenarios.disaster import DISASTER
from .scenarios.night import NIGHT


SCENARIOS = [

    NORMAL_DAY,

    SCHOOL_HOURS,

    HARVEST,

    MARKET_DAY,

    FESTIVAL,

    RAINFALL,

    DISASTER,

    NIGHT,

]