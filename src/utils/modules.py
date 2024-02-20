import itertools
import collections
from config.geometry.BPix.name_position_map import name_position_map_bpix
from config.geometry.FPix.name_position_map import name_position_map_fpix
from config.geometry.BPix.module_size import module_size_bpix
from config.geometry.FPix.module_size import module_size_fpix


PositionCoordinates = collections.namedtuple('Coordinate', ["r", "phi", "z"])
SizeCoordinates = collections.namedtuple('Coordinate', ["r", "rphi", "z"])


class BPixModule:
    """Class representing a BPix module."""

    def __init__(self, name):
        """BPix module constructor.
        
        Args:
            name (str): Module name, e.g. BPix_BmI_SEC4_LYR1_LDR3F_MOD1
        """

        self.name = name
        if name not in name_position_map_bpix:
            raise ValueError("Invalid BPix module name {name}")
        position = name_position_map_bpix[self.name]
        self.position = PositionCoordinates(*position)
        self.size = SizeCoordinates(*module_size_bpix)

    def getAverageFluence(self, fluence_field, lumi, pp_cross_section, dz=0.1):
        """
        Args:
            fluence_field (ROOT.TH2F): Fluence field, in n_eq.cm-2
            lumi (float): Integrated luminosity in fb-1 (resp. fb-1.s-1)
            pp_cross_section (float): proton-proton total cross-section in mb
            dz (float): axial integration element in cm
    
        Returns:
            float: Fluence for the module, in n_eq.cm-2 (resp. n_eq.cm-2.s-1)
        """

        lumi *= 1e-15  # convert from /fb to /b
        pp_cross_section *= 10**27  # convert from mb to cm2

        z = self.position.z - self.size.z/2. + dz/2.
        phi_eq = 0
        while z < self.position.z + self.size.z/2.:
            phi_eq += fluence_field.GetBinContent(
                fluence_field.GetXaxis().FindBin(self.position.r),
                fluence_field.GetYaxis().FindBin(z)
            )
            z += dz

        return (dz/self.size.z) * phi_eq * lumi * pp_cross_section


class FPixModule:
    """Class representing a FPix module."""

    def __init__(self, name):
        """FPix module constructor.
        
        Args:
            name (str): Module name, e.g. FPix_BpI_D1_BLD6_PNL2_RNG1
        """

        self.name = name
        if name not in name_position_map_fpix:
            raise ValueError("Invalid FPix module name {name}")
        position = name_position_map_fpix[name]
        self.position = PositionCoordinates(*position)
        self.size = SizeCoordinates(*module_size_fpix)

    def getAverageFluence(self, fluence_field, lumi, pp_cross_section, dr=0.1):
        """
        Args:
            fluence_field (ROOT.TH2F): Fluence field, in n_eq.cm-2
            lumi (float): Integrated luminosity in fb-1
            pp_cross_section (float): proton-proton total cross-section in mb
            dr (float): radial integration element in cm
    
        Returns:
            float: Fluence for the module, in n_eq.cm-2
        """

        lumi *= 1e-15  # convert from /fb to /b
        pp_cross_section *= 10**27  # convert from mb to cm2

        r = self.position.r - self.size.r/2. + dr/2.
        phi_eq = 0
        while r < self.position.r + self.size.r/2.:
            phi_eq += fluence_field.GetBinContent(
                fluence_field.GetXaxis().FindBin(r),
                fluence_field.GetYaxis().FindBin(self.position.z)
            )
            r += dr

        return (dr/self.size.r) * phi_eq * lumi * pp_cross_section


class ReadoutGroup:
    """Class representing a BPix or FPix readout group."""

    def __init__(self, name):
        """ReadoutGroup constructor.
        
        Args:
            name (str): Read out group name, a.k.a. sector name, e.g. BPix_BmI_SEC4_LYR1
        """

        self.name = name
        sub_system = name.split("_")[0]
        self.list_of_modules = []

        if sub_system not in ["FPix", "BPix"]:
            raise ValueError(f"Invalid read out group {name}")

        if sub_system == "BPix":
            name_position_map = name_position_map_bpix
            for module_name in name_position_map.keys():
                if module_name.startswith(name): 
                    self.list_of_modules.append(BPixModule(module_name))
        else:
            name_position_map = name_position_map_fpix
            raise NotImplementedError
        
        if len(self.list_of_modules) == 0:
            raise ValueError(f"Invalid read out group name {name}")

    def getAverageAzimuthalAngle(self):
        """Return average azimuthal angle over the modules in this readout group."""

        phi_average = 0.
        for module in self.list_of_modules:
            phi_average += module.position.phi
        phi_average /= len(self.list_of_modules)

        return phi_average

    def getAverageFluence(self, fluence_field, lumi, pp_cross_section, dx=0.1):
        """Return average fluence over the modules in this readout group.

        Args:
            fluence_field (ROOT.TH2F): Fluence field, in n_eq.cm-2
            lumi (float): Integrated luminosity in fb-1 (resp. fb-1.s-1)
            pp_cross_section (float): proton-proton total cross-section in mb
            dx (float): infinitesimal integration element in cm
    
        Returns:
            float: Fluence for the module, in n_eq.cm-2 (resp. n_eq.cm-2.s-1)
        """

        fluence = 0
        for module in self.list_of_modules:
            fluence += module.getAverageFluence(fluence_field, lumi, pp_cross_section, dx)
        # fluence /= len(self.list_of_modules)
        return fluence


class BPixLayer:
    """Class representing a BPix layer."""

    def __init__(self, layer):
        """BPixLayer constructor.
        
        Args:
            layer (int): Layer number
        """

        self.layer = layer

        half_cyclinders = ("BpO", "BmO", "BpI", "BmI")
        sectors = range(1, 9)
        self.list_of_sectors_names = [
            "BPix_%s_SEC%s_LYR%s" % (half_cyclinder, sector, layer)
            for half_cyclinder, sector in itertools.product(half_cyclinders, sectors)
        ]

        self.list_of_sectors = [
            ReadoutGroup(sector_name) for sector_name in self.list_of_sectors_names
        ]

    def getAverageFluence(self, fluence_field, lumi, pp_cross_section, dx=0.1):
        """Return average fluence over all the sectors in this readout group.

        Args:
            fluence_field (ROOT.TH2F): Fluence field, in n_eq.cm-2
            lumi (float): Integrated luminosity in fb-1 (resp. fb-1.s-1)
            pp_cross_section (float): proton-proton total cross-section in mb
            dx (float): infinitesimal integration element in cm
    
        Returns:
            float: Fluence for the module, in n_eq.cm-2 (resp. n_eq.cm-2.s-1)
        """

        fluence = 0
        for module in self.list_of_sectors:
            fluence += module.getAverageFluence(fluence_field, lumi, pp_cross_section, dx)
        # fluence /= len(self.list_of_sectors)
        return fluence
