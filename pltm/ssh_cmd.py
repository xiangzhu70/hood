import os
import paramiko
import logging

paramiko_logger = logging.getLogger('paramiko')
paramiko_logger.setLevel(logging.WARNING)

class SshCommand:
    def __init__(self, logger):
        self.logger = logger
        private_key_path = os.path.expanduser('~/.ssh/id_ed25519')
        try:
            self.private_key = paramiko.Ed25519Key.from_private_key_file(private_key_path)
            # Use private_key for SSH authentication
        except paramiko.ssh_exception.SSHException as e:
            self.logger.info(f"Error loading private key: {e}")

    # This is debuggedd to work with the jump settings in my .ssh/config.
    # More debugging is needed to handle the variations.
    def host_connect(self, hostname, username, port=22, ssh_config=None):
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
            intermediate_ssh = self.host_connect(jump_hostname, jump_username, ssh_config=ssh_config)
            sock = intermediate_ssh.get_transport().open_channel('direct-tcpip', (final_hostname, port), ('', 0))
            self.logger.debug(f"proxy_jump final connect: hostname {final_hostname}, username {username}, key {self.private_key}")
            ssh.connect(hostname=final_hostname, username=username, port=port, sock=sock, pkey=self.private_key)
        else:
            self.logger.debug(f"no more jump.  connect to final_hostname {final_hostname}, username {username}"
                             f", key {self.private_key}")
            ssh.connect(hostname=final_hostname,
                        username=username,
                        pkey=self.private_key)
        return ssh

    def ssh_run(self, host, username, cmd):
        ssh = self.host_connect(host, username)
        channel = ssh.get_transport().open_session()

        lines = []
        channel.exec_command(cmd)
        try:
            while True:
                data = channel.recv(1024)
                if not data:
                    break
                lines.append(data.decode('utf-8'))
                #self.logger.info(data.decode('utf-8'))
        except KeyboardInterrupt:
            self.logger.info("sending ctrl-c")
            channel.sendall(b'\x03')

        channel.close()
        ssh.close()

        return lines
