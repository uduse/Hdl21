"""
# Hdl21 Primitive Modules

Primitives are leaf-level Modules typically defined not by users, 
but by simulation tools or device fabricators. 
Prominent examples include MOS transistors, diodes, resistors, and capacitors. 

Primitives divide in two classes, `physical` and `ideal`, indicated by their `primtype` attribute. 
`PrimitiveType.IDEAL` primitives specify circuit-theoretic ideal elements 
e.g. resistors, capacitors, inductors, and notably aphysical elements 
such as ideal voltage and current sources. 

`PrimitiveType.PHYSICAL` primitives in contrast specify abstract versions 
of ultimately physically-realizable elements such as transistors and diodes. 
These elements typically require some external translation, e.g. by a process-technology 
library, to execute in simulations or to be realized in hardware. 

Many element-types (particularly passives) come in both `ideal` and `physical` flavors, 
as typical process-technologies include physical passives, but with far different 
parameterization than ideal passives. For example resistors are commonly specified 
in physical length and width. Capacitors are similarly specified in physical terms, 
often adding metal layers or other physical features. The component-value (R,C,L, etc.) 
for these physically-specified cells is commonly suggestive or optional. 

| Ideal              | Alias(es)         | Physical           | Alias(es)      |
| ------------------ | ----------------- | ------------------ | -------------- |
| IdealResistor      | R, Res, Resistor  | PhysicalResistor   |                |
| IdealInductor      | L, Ind, Inductor  | PhysicalInductor   |                |
| IdealCapacitor     | C, Cap, Capacitor | PhysicalCapacitor  |                |
| DcVoltageSource    | Vsrc, Vdc, V      |                    |                |
| PulseVoltageSource | Vpulse, Vpu       |                    |                |
| CurrentSource      | Isrc, Idc, I      |                    |                |
|                    |                   | Mos                | Nmos, Pmos     |
|                    |                   | Bipolar            | Bjt, Npn, Pnp  |
|                    |                   | Diode              | D              |
|                    |                   | PhysicalShort      | Short          |

"""

import copy
from dataclasses import replace
from enum import Enum
from typing import Optional, Any, List, Type, Union
from pydantic.dataclasses import dataclass

# Local imports
from .params import paramclass, Param, isparamclass, NoParams
from .signal import Port, Signal, Visibility
from .instance import calls_instantiate
from .prefix import Prefixed

# Type alias for many scalar parameters
ScalarParam = Union[Prefixed, int, float, str]
ScalarOption = Optional[ScalarParam]


class PrimitiveType(Enum):
    """ Enumerated Primitive-Types """

    IDEAL = "IDEAL"
    PHYSICAL = "PHYSICAL"


@dataclass
class Primitive:
    """ # Hdl21 Primitive Component

    Primitives are leaf-level Modules typically defined not by users,
    but by simulation tools or device fabricators.
    Prominent examples include MOS transistors, diodes, resistors, and capacitors.
    """

    name: str  # Primitive Name
    desc: str  # String Description
    port_list: List[Signal]  # Ordered Port List
    paramtype: Type  # Class/ Type of valid Parameters
    primtype: PrimitiveType  # Ideal vs Physical Primitive-Type

    def __post_init_post_parse__(self):
        """ After type-checking, do plenty more checks on values """
        if not isparamclass(self.paramtype):
            msg = f"Invalid Primitive param-type {self.paramtype} for {self.name}, must be an `hdl21.paramclass`"
            raise TypeError(msg)
        for p in self.port_list:
            if not p.name:
                raise ValueError(f"Unnamed Primitive Port {p} for {self.name}")
            if p.vis != Visibility.PORT:
                msg = f"Invalid Primitive Port {p.name} on {self.name}; must have PORT visibility"
                raise ValueError(msg)

    def __call__(self, params: Any = NoParams) -> "PrimitiveCall":
        return PrimitiveCall(prim=self, params=params)

    @property
    def Params(self) -> Type:
        return self.paramtype

    @property
    def ports(self) -> dict:
        return {p.name: p for p in self.port_list}


@calls_instantiate
@dataclass
class PrimitiveCall:
    """ Primitive Call
    A combination of a Primitive and its Parameter-values,
    typically generated by calling the Primitive. """

    prim: Primitive
    params: Any = NoParams

    def __post_init_post_parse__(self):
        # Type-validate our parameters
        if not isinstance(self.params, self.prim.paramtype):
            msg = f"Invalid parameters {self.params} for Primitive {self.prim}. Must be {self.prim.paramtype}"
            raise TypeError(msg)

    @property
    def ports(self) -> dict:
        return self.prim.ports


""" 
Mos Transistor Section 
"""


class MosType(Enum):
    """ NMOS/PMOS Type Enumeration """

    NMOS = "NMOS"
    PMOS = "PMOS"


class MosVth(Enum):
    """ MOS Threshold Enumeration """

    STD = "STD"
    LOW = "LOW"
    HIGH = "HIGH"


@paramclass
class MosParams:
    """ MOS Transistor Parameters """

    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)
    npar = Param(dtype=int, desc="Number of parallel fingers", default=1)
    tp = Param(dtype=MosType, desc="MosType (PMOS/NMOS)", default=MosType.NMOS)
    vth = Param(dtype=MosVth, desc="Threshold voltage specifier", default=MosVth.STD)
    model = Param(
        dtype=Optional[str], desc="Model (Name)", default=None
    )  # FIXME: whether to include

    def __post_init_post_parse__(self):
        """ Value Checks """
        if self.w <= 0:
            raise ValueError(f"MosParams with invalid width {self.w}")
        if self.l <= 0:
            raise ValueError(f"MosParams with invalid length {self.l}")
        if self.npar <= 0:
            msg = f"MosParams with invalid number parallel fingers {self.npar}"
            raise ValueError(msg)


MosPorts = [Port(name="d"), Port(name="g"), Port(name="s"), Port(name="b")]

Mos = Primitive(
    name="Mos",
    desc="Mos Transistor",
    port_list=copy.deepcopy(MosPorts),
    paramtype=MosParams,
    primtype=PrimitiveType.PHYSICAL,
)


def Nmos(params: MosParams) -> Primitive:
    """ Nmos Constructor. A thin wrapper around `hdl21.primitives.Mos` """
    return Mos(replace(params, tp=MosType.NMOS))


def Pmos(params: MosParams) -> Primitive:
    """ Pmos Constructor. A thin wrapper around `hdl21.primitives.Mos` """
    return Mos(replace(params, tp=MosType.PMOS))


@paramclass
class DiodeParams:
    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)
    model = Param(
        dtype=Optional[str], desc="Model (Name)", default=None
    )  # FIXME: whether to include


Diode = Primitive(
    name="Diode",
    desc="Diode",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=DiodeParams,
    primtype=PrimitiveType.PHYSICAL,
)


# Common alias(es)
D = Diode

""" 
Passives
"""


@paramclass
class ResistorParams:
    r = Param(dtype=float, desc="Resistance (ohms)")


IdealResistor = Primitive(
    name="IdealResistor",
    desc="Ideal Resistor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=ResistorParams,
    primtype=PrimitiveType.IDEAL,
)


# Common aliases
R = Res = Resistor = IdealResistor


@paramclass
class PhysicalResistorParams:
    r = Param(dtype=float, desc="Resistance (ohms)")


PhysicalResistor = Primitive(
    name="PhysicalResistor",
    desc="Physical Resistor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=ResistorParams,
    primtype=PrimitiveType.PHYSICAL,
)


@paramclass
class IdealCapacitorParams:
    c = Param(dtype=float, desc="Capacitance (F)")


IdealCapacitor = Primitive(
    name="IdealCapacitor",
    desc="Ideal Capacitor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=IdealCapacitorParams,
    primtype=PrimitiveType.IDEAL,
)


# Common aliases
C = Cap = Capacitor = IdealCapacitor


@paramclass
class PhysicalCapacitorParams:
    c = Param(dtype=float, desc="Capacitance (F)")


PhysicalCapacitor = Primitive(
    name="PhysicalCapacitor",
    desc="Physical Capacitor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PhysicalCapacitorParams,
    primtype=PrimitiveType.PHYSICAL,
)


@paramclass
class IdealInductorParams:
    l = Param(dtype=float, desc="Inductance (H)")


IdealInductor = Primitive(
    name="IdealInductor",
    desc="Ideal Inductor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=IdealInductorParams,
    primtype=PrimitiveType.IDEAL,
)


# Common alias(es)
L = Inductor = IdealInductor


@paramclass
class PhysicalInductorParams:
    l = Param(dtype=float, desc="Inductance (H)")


PhysicalInductor = Primitive(
    name="PhysicalInductor",
    desc="Physical Inductor",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PhysicalInductorParams,
    primtype=PrimitiveType.PHYSICAL,
)


@paramclass
class PhysicalShortParams:
    layer = Param(dtype=Optional[int], desc="Metal layer", default=None)
    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)


PhysicalShort = Primitive(
    name="PhysicalShort",
    desc="Short-Circuit/ Net-Tie",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PhysicalShortParams,
    primtype=PrimitiveType.PHYSICAL,
)

# Common alias(es)
Short = PhysicalShort


""" 
Sources
"""


@paramclass
class DcVoltageSourceParams:
    """ `DcVoltageSource` Parameters """

    dc = Param(dtype=ScalarOption, default=0, desc="DC Value (V)")
    ac = Param(dtype=ScalarOption, default=None, desc="AC Amplitude (V)")


DcVoltageSource = Primitive(
    name="DcVoltageSource",
    desc="Ideal DC Voltage Source",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=DcVoltageSourceParams,
    primtype=PrimitiveType.IDEAL,
)

# Common alias(es)
V = Vdc = Vsrc = DcVoltageSource


@paramclass
class PulseVoltageSourceParams:
    """ `PulseVoltageSource` Parameters """

    delay = Param(dtype=ScalarOption, default=None, desc="Time Delay (s)")
    v1 = Param(dtype=ScalarOption, default=None, desc="One Value (V)")
    v2 = Param(dtype=ScalarOption, default=None, desc="Zero Value (V)")
    period = Param(dtype=ScalarOption, default=None, desc="Period (s)")
    rise = Param(dtype=ScalarOption, default=None, desc="Rise time (s)")
    fall = Param(dtype=ScalarOption, default=None, desc="Fall time (s)")
    width = Param(dtype=ScalarOption, default=None, desc="Pulse width (s)")


PulseVoltageSource = Primitive(
    name="PulseVoltageSource",
    desc="Pulse Voltage Source",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=PulseVoltageSourceParams,
    primtype=PrimitiveType.IDEAL,
)

# Common alias(es)
Vpu = Vpulse = PulseVoltageSource


@paramclass
class CurrentSourceParams:
    dc = Param(dtype=ScalarOption, default=0, desc="DC Value (A)")


CurrentSource = Primitive(
    name="CurrentSource",
    desc="Ideal DC Current Source",
    port_list=[Port(name="p"), Port(name="n")],
    paramtype=CurrentSourceParams,
    primtype=PrimitiveType.IDEAL,
)

# Common alias(es)
I = Idc = Isrc = CurrentSource


""" 
Bipolar Section 
"""


class BipolarType(Enum):
    """ Bipolar Junction Transistor NPN/PNP Type Enumeration """

    NPN = "NPN"
    PNP = "PNP"


@paramclass
class BipolarParams:
    """ Bipolar Transistor Parameters """

    w = Param(dtype=Optional[int], desc="Width in resolution units", default=None)
    l = Param(dtype=Optional[int], desc="Length in resolution units", default=None)
    tp = Param(
        dtype=BipolarType, desc="Bipolar Type (NPN/ PNP)", default=BipolarType.NPN
    )

    def __post_init_post_parse__(self):
        """ Value Checks """
        if self.w <= 0:
            raise ValueError(f"BipolarParams with invalid width {self.w}")
        if self.l <= 0:
            raise ValueError(f"BipolarParams with invalid length {self.l}")


Bipolar = Primitive(
    name="Bipolar",
    desc="Bipolar Transistor",
    port_list=[Port(name="c"), Port(name="b"), Port(name="e")],
    paramtype=BipolarParams,
    primtype=PrimitiveType.PHYSICAL,
)

# Common alias(es)
Bjt = Bipolar


def Npn(params: BipolarParams) -> Primitive:
    """ Npn Constructor. A thin wrapper around `hdl21.primitives.Bipolar` """
    return Bipolar(replace(params, tp=BipolarType.NPN))


def Pnp(params: BipolarParams) -> Primitive:
    """ Pnp Constructor. A thin wrapper around `hdl21.primitives.Bipolar` """
    return Bipolar(replace(params, tp=BipolarType.PNP))
