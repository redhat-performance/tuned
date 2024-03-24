from . import base

PROCESSOR_NAME = ("sandybridge",
        "ivybridge",
        "haswell",
        "broadwell",
        "skylake")

PMU_PATH = "/sys/devices/cpu/caps/pmu_name"
ACTIVE = "active"
DISABLE = "disable"

class intel_recommended_pstate(base.Function):
    """
    Checks the processor code name and return the recommended
    intel_pstate CPUFreq driver mode. Active is returned for the
    newer generation of processors not in the PROCESSOR_NAME list.

    Intel recommends to use the intel_pstate CPUFreq driver
    in active mode with HWP enabled on Ice Lake and later 
    generations processors. This function allows dynamically 
    setting intel_pstate based on the processor's model.
    For pre-IceLake processors setting pstate to active
    can introduce jitters which were historically seen around
    and tested with RHEL-7.4. From IceLake generation, intel 
    has fixed these issues. 
    """
    def __init__(self):
        super(intel_recommended_pstate, self).__init__("intel_recommended_pstate", 0)

    def execute(self, args):
        if not super(intel_recommended_pstate, self).execute(args):
            return None

        current_processor_name = self._cmd.read_file(PMU_PATH).strip()
        if current_processor_name == "" or current_processor_name in PROCESSOR_NAME:
            return DISABLE
        return ACTIVE