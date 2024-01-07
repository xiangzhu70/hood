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
        # if shell==True, use the raw cmd as the calling param
        if not shell:
            cmd_param = shlex.split(cmd)
        else:
            cmd_param = cmd

        output = []
        process = subprocess.Popen(cmd_param, shell=shell,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        while True:
            line = process.stdout.readline()
            if line == '' and process.poll() is not None:
                break
            if line:
                line = line.strip()
                output.append(line)
                print(line)
        rc = process.poll()
        print(f"process return {rc}")
        return output
