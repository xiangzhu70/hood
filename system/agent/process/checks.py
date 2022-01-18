from diag_check import Check

class CheckAgentProcessUp(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":platform.kernel:up == OK",
            ".:run_env == OK",
            ".:not_crashing == OK",
            ".:no_asic_error == OK",
        ]

class CheckAgentRunEnv(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.ok_necessary_conditions = [
            ":asic:presence == OK",
            ":platform.kernel:cmdline == OK",
            ":sdk.sdk_kmod:loaded == OK",
            ":provision:fbwhoami == OK",
            ":provision:fruid == OK",
        ]

class CheckAgentProcessNotCrashing(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Look into crash log\nOncall: fboss-dev"

class CheckAgentProcessNoAsicError(Check):
    def __init__(self, inst_name):
        super().__init__(inst_name)
        self.action_on_fail = "[investigate]Look into ASIC error log\nOncall: fboss-dev"


