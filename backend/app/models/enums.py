import enum


class Role(str, enum.Enum):
    farmer = "farmer"
    vet = "vet"
    regulator = "regulator"
    admin = "admin"


class Species(str, enum.Enum):
    cattle = "cattle"
    buffalo = "buffalo"
    goat = "goat"
    sheep = "sheep"
    pig = "pig"
    poultry = "poultry"


class ProductionStatus(str, enum.Enum):
    dry = "dry"
    lactating = "lactating"
    laying = "laying"
    growing = "growing"
    fattening = "fattening"


class Sex(str, enum.Enum):
    female = "female"
    male = "male"


class AnimalStatus(str, enum.Enum):
    active = "active"
    sold = "sold"
    dead = "dead"


class Tissue(str, enum.Enum):
    milk = "milk"
    meat = "meat"
    eggs = "eggs"


class AWaReClass(str, enum.Enum):
    Access = "Access"
    Watch = "Watch"
    Reserve = "Reserve"


class Route(str, enum.Enum):
    oral = "oral"
    im = "im"
    iv = "iv"
    sc = "sc"
    intra_mammary = "intra_mammary"
    in_water = "in_water"


class WithdrawalStatus(str, enum.Enum):
    active = "active"
    cleared = "cleared"


class SaleProduct(str, enum.Enum):
    milk = "milk"
    meat = "meat"
    eggs = "eggs"
    live_animal = "live_animal"


class BuyerType(str, enum.Enum):
    local_dairy = "local_dairy"
    mandi = "mandi"
    processor = "processor"
    individual = "individual"


class ResidueResult(str, enum.Enum):
    pending = "pending"
    pass_ = "pass"
    fail = "fail"


class AlertSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    critical = "critical"


class AlertType(str, enum.Enum):
    MRL_VIOLATION = "MRL_VIOLATION"
    MRL_VIOLATION_CONFIRMED = "MRL_VIOLATION_CONFIRMED"
    PROHIBITED_DRUG_USED = "PROHIBITED_DRUG_USED"
    WITHDRAWAL_ACTIVE_AT_SALE = "WITHDRAWAL_ACTIVE_AT_SALE"
    NEAR_MISS_SALE = "NEAR_MISS_SALE"
    UPCOMING_CLEARANCE = "UPCOMING_CLEARANCE"
    ML_MRL_RISK_HIGH = "ML_MRL_RISK_HIGH"
    OUTBREAK_RISK = "OUTBREAK_RISK"
    SENSOR_ANOMALY = "SENSOR_ANOMALY"
    GEOFENCE_BREACH = "GEOFENCE_BREACH"
    INSTALL_UPDATE = "INSTALL_UPDATE"


class AlertAudience(str, enum.Enum):
    all = "all"          # every role with farm visibility
    farmer = "farmer"    # visible only to the owning farmer


class VisitStatus(str, enum.Enum):
    requested = "requested"
    scheduled = "scheduled"
    completed = "completed"
    cancelled = "cancelled"


class PreferredSlot(str, enum.Enum):
    morning = "morning"
    afternoon = "afternoon"
    evening = "evening"


class LedgerEventType(str, enum.Enum):
    animal_registered = "animal_registered"
    administration = "administration"
    sale_event = "sale_event"
    residue_test = "residue_test"
    alert_raised = "alert_raised"
