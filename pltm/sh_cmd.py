import subprocess
import shlex

class ShellCommand:
    def __init__(self, logger):
        self.logger = logger

    def run_cmd(self, cmd, shell=False, realtime=False, timeout=1):
        self.logger.info(f"== sh run_cmd [{cmd}]")
        if realtime:
            return self._run_cmd_realtime(cmd, shell=shell, timeout=timeout)

        try:
            cmpl = subprocess.run(shlex.split(cmd),
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=timeout, shell=shell)
            output = cmpl.stdout.decode().strip()
        except Exception as e:
            output = str(e)

        self.logger.info("-- output: ")
        self.logger.info(output)
        self.logger.info("-- output end")

        return output

    def _run_cmd_realtime(self, cmd, shell=False, timeout=100):
        if not shell:
            cmd_param = shlex.split(cmd)
        else:
            cmd_param = cmd
            # if shell==True, use the raw cmd as the calling param
        try:
            cmpl = subprocess.run(cmd_param,
                                  # stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  timeout=timeout, shell=shell)
            stdout = cmpl.stdout
            if isinstance(stdout, bytes):
                output = stdout.decode().strip()
            elif not output:
                output = "None"
            else:
                output = stdout
        except Exception as e:
            output = str(e)
        return output