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
    Returns the recommended intel_pstate CPUFreq driver mode
    based on the CPU generation.

    NOTE: Intel recommends to use the P-State driver
    in active mode with HWP enabled starting from the Ice Lake
    CPU generations. In older CPU generations, setting
    P-State to `active` can introduce jitters which were historically
    seen around and tested with RHEL-7.4. Beginning with the Ice Lake
    generation, Intel has fixed these issues.
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
