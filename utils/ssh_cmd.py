import os
import paramiko
import logging
import time
import socket

paramiko_logger = logging.getLogger('paramiko')
paramiko_logger.setLevel(logging.WARNING)

class SshCommand:
    def __init__(self, logger):
        self.logger = logger
        self.private_key = None

    def init_key(self):
        # this should be generalized, not assuming one type of key  TBD
        private_key_path = os.path.expanduser('~/.ssh/id_ed25519')
        try:
           self.private_key = paramiko.Ed25519Key.from_private_key_file(private_key_path)
        except paramiko.ssh_exception.SSHException as e:
            self.logger.info(f"Error loading private key: {e}")

    # This is debuggedd to work with the jump settings in my .ssh/config.
    # More debugging is needed to handle the variations.
    def host_connect(self, hostname, username, password=None, port=22, ssh_config=None, timeout=10):
        if not password and not self.private_key:
            self.init_key()

        self.logger.debug(f"host_connect: hostname {hostname}, username {username}")
        if not ssh_config:
            ssh_config = paramiko.SSHConfig()
            with open(os.path.expanduser('~/.ssh/config')) as f:
                ssh_config.parse(f)
        host_config = ssh_config.lookup(hostname)
        self.logger.debug(f"found host_config for {hostname}")
        final_hostname = host_config.get('hostname')
        proxy_jump = host_config.get('proxyjump')

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if proxy_jump:
            self.logger.debug(f"proxy_jump: {proxy_jump}")
            jump_fields = proxy_jump.split('@')
            jump_username = jump_fields[0]
            jump_hostname = jump_fields[1]
            intermediate_ssh = self.host_connect(jump_hostname, jump_username, password=password, ssh_config=ssh_config, timeout=timeout)
            sock = intermediate_ssh.get_transport().open_channel('direct-tcpip', (final_hostname, port), ('', 0))
            self.logger.debug(f"proxy_jump final connect: hostname {final_hostname}, username {username}")
            if password:
                self.logger.debug(f"password {password}")
            else:
                self.logger.debug(f"key {self.private_key}")
            if password:
                ssh.connect(hostname=final_hostname, username=username, port=port, sock=sock, password=password)
            else:
                ssh.connect(hostname=final_hostname, username=username, port=port, sock=sock, pkey=self.private_key)
        else:
            self.logger.debug(f"no more jump.  connect to final_hostname {final_hostname}, username {username}")
            #import pdb; pdb.set_trace()
            if password:
                self.logger.debug(f"password {password}")
            else:
                self.logger.debug(f"key {self.private_key}")
            if password:
                ssh.connect(hostname=final_hostname, username=username, password=password, timeout=timeout)
            else:     
                ssh.connect(hostname=final_hostname, username=username, pkey=self.private_key, timeout=timeout)
            self.logger.debug(f"{final_hostname} connected")
        return ssh

    def run_cmd_with_channel(self, ssh, cmd, tail, timeout=5):
        channel = ssh.get_transport().open_session()
        if not tail:
            channel.settimeout(timeout)

        channel.exec_command(cmd)
            
        count = 0
        lines = []

        try:
            start_time = time.time()
            while True:

                # commented out the below because recv can return when
                # there is no data
                # #Check if any data is available before receiving
                # if not channel.recv_ready():
                #     if not tail and (time.time() - start_time > timeout):
                #         print(f"timed out after {timeout} sec on cmd <{cmd}>")
                #         raise TimeoutError("No data received within timeout")
                #     # Slightly delay further checks to avoid unnecessary CPU usage
                #     time.sleep(0.01)
                #     continue

                data = channel.recv(1024)
                if not data:
                    #print(f"no more data on cmd <{cmd}>")                 
                    break
                decoded = data.decode('utf-8')
                new_lines = decoded.splitlines()
                for line in new_lines:
                    if tail:
                        self.logger.info(line)
                    else:
                        lines.append(line)

        except socket.timeout:
            print(f"ssh channel socket timeout on cmd [{cmd}].")
        except (TimeoutError, KeyboardInterrupt) as e:
            if isinstance(e, KeyboardInterrupt):
                self.logger.info("sending ctrl-c")
                channel.sendall(b'\x03')
            else:
                print(f"Timeout reached: {e}")
        finally:
            channel.close()

        return lines

    # Function to send command to the shell
    def send_shell_cmd(self, shell, command, timeout=5):
        if shell.recv_ready():
            output = shell.recv(4096).decode('utf-8')
            # shell initial message not caused by the command
            # should be thrown away
            # print("throw away shell initial message--<")
            # print(output)
            # print(">--")
        
        shell.send(command + '\n')

        
        # Receive output from the shell
        ready = False
        count_remain = timeout
        while not ready:
            ready = shell.recv_ready()
            if ready:
                break
            count_remain -= 1
            if count_remain <= 0:
                break
            time.sleep(1)
        if not ready:
            print(f"send_shell_cmd: timed out after {timeout}")
            return ""
        output = shell.recv(4096).decode('utf-8')
        return output

    def run_cmd_in_shell(self, ssh, cmd, tail, timeout=5):
        shell = ssh.invoke_shell()

        cmds = cmd.splitlines()

        output_lines = []
        for one_cmd in cmds:
            output = self.send_shell_cmd(shell, one_cmd, timeout=timeout)
            if tail:
                print(output)
            else:
                output_lines.extend(output.splitlines())

        return output_lines

    # For long-running command we wait for output, set tail to true.
    # There will be no timeout.  Use ctrl-c to abort it.
    # Otherwise, it is just one short run.  stop if there is no more 
    # output in 2 sec.
    def run_cmd(self, host, username, cmd, password=None, shell=False, tail=False, timeout=5):
        self.logger.info(f"== ssh <{host}, {username}> run_cmd [{cmd}]")
        ssh = self.host_connect(host, username, password=password, timeout=timeout)

        if shell:
            lines = self.run_cmd_in_shell(ssh, cmd, tail, timeout=timeout)
        else:
            lines = self.run_cmd_with_channel(ssh, cmd, tail, timeout=timeout)
        
        ssh.close()

        if not tail:
            self.logger.info("-- output: ")
            for line in lines:
                self.logger.info(line)
            self.logger.info("-- output end")
        return lines
