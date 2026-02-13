#!/usr/bin/env python3
"""
Network Utilities Module

Professional network automation utilities for Juniper devices with support for:
- Junos device connections
- Jumphost/bastion host access
- File transfers (SCP)
- Email notifications

Author: Grasshopper Automation
"""

import os
# import sys
import logging
from typing import Optional, List, Tuple, Any#, Dict
from typing_extensions import TypedDict, Unpack
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path

# Juniper PyEZ imports
from jnpr.junos import Device
from jnpr.junos.utils.start_shell import StartShell
from jnpr.junos.exception import ConnectError, ConnectAuthError

# SSH and SCP imports
from paramiko import SSHClient, AutoAddPolicy
from paramiko.ssh_exception import SSHException, AuthenticationException
from scp import SCPClient

# Email imports
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import smtplib

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class VariableInfo(TypedDict, total=False):
    """Type definition for initialization parameters"""
    hostname: str
    username: str
    password: str
    port: int
    dst_host: str
    dst_username: str
    dst_password: str
    directory_path: str
    filename: str
    src_path: str
    dst_path: str
    email_from: str
    email_to: str
    email_subject: str
    email_body: str
    greeting: str
    cc_emails: List[str]
    destination_path: str
    attach_list: List[str]


class NwUtilities:
    """
    Network Utilities for Juniper device management and automation.

    This class provides functionality for:
    - Connecting to Juniper devices via PyEZ
    - Accessing devices through jumphosts
    - File transfer operations
    - Email notifications

    Attributes:
        config (ConfigParser): Configuration file parser
    """

    # def __init__(self, **kwargs: Unpack[VariableInfo]):
    def __init__(self):
        """
        Initialize NwUtilities with connection parameters.

        Parameters can be provided via kwargs or loaded from _config.ini file.

        Args:
            #**kwargs: Configuration parameters as defined in VariableInfo

        Raises:
            FileNotFoundError: If config file is not found
        """
        # Initialize config parser
        self.config = ConfigParser()
        config_file = './_config.ini'

        if not os.path.exists(config_file):
            logger.warning(f"Config file '{config_file}' not found. Using kwargs only.")
        else:
            self.config.read(config_file)

        # # Connection parameters
        # self.HOST = kwargs.get('hostname', '')
        # self.USER = kwargs.get('username', '')
        # self.PASS = kwargs.get('password', '')
        # self.PORT = kwargs.get('port', '22')
        # # self.HOST = kwargs.get('hostname') or self._get_config('lab_device', 'host_ip')
        # # self.USER = kwargs.get('username') or self._get_config('lab_device', 'username')
        # # self.PASS = kwargs.get('password') or self._get_config('lab_device', 'password')
        # # self.PORT = kwargs.get('port') or int(self._get_config('lab_device', 'port', 22))
        #
        # # Jumphost/file parameters
        # self.dst_host = kwargs.get('dst_host', '')
        # self.directory_path = kwargs.get('directory_path', '')
        # self.filename = kwargs.get('filename', '')
        # self.src_path = kwargs.get('src_path', '')
        # self.dst_path = kwargs.get('dst_path', '')
        #
        # # Email parameters
        # self.email_from = kwargs.get('email_from', '')
        # self.email_to = kwargs.get('email_to', '')
        # self.email_subject = kwargs.get('email_subject', '')
        # self.email_body = kwargs.get('email_body', '')
        # self.greeting = kwargs.get('greeting', '')
        # self.cc_emails = kwargs.get('cc_emails', [])
        # self.destination_path = kwargs.get('destination_path', '')
        # self.attach_list = kwargs.get('attach_list', [])

        # Active connections
        self._junos_device = None
        self._jumphost_client = None
        self._target_client = None

        # logger.info(f"NwUtilities initialized for host: {self.HOST}")

    def _get_config(self, section: str, key: str, default: Any = None) -> Any:
        """
        Safely get configuration value.

        Args:
            section: Config section name
            key: Config key name
            default: Default value if not found

        Returns:
            Configuration value or default
        """
        try:
            return self.config.get(section, key)
        except Exception:
            return default

    # ==========================================
    # Junos Connection Methods
    # ==========================================

    def junos_open_connection(self,
                              hostname: Optional[str] = None,
                              username: Optional[str] = None,
                              password: Optional[str] = None,
                              port: Optional[int] = 22) -> Optional[Device]:
        """
        Open connection to Juniper device using PyEZ.

        Returns:
            Device: Connected Junos device object

        Raises:
            ConnectError: If connection fails
            ConnectAuthError: If authentication fails
        """
        if self._junos_device is not None:
            logger.info("Junos connection already open")
            return self._junos_device

        try:
            logger.info(f"Connecting to Junos device: {hostname}")

            dev = Device(
                host=hostname,
                user=username,
                passwd=password,
                port=port
            )
            dev.open()

            self._junos_device = dev
            logger.info(f"Successfully connected to {dev.hostname}")

            return dev

        except ConnectAuthError as e:
            logger.error(f"Authentication failed for {hostname}: {e}")
            raise
        except ConnectError as e:
            logger.error(f"Connection failed to {hostname}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to {hostname}: {e}")
            raise

    def junos_close_connection(self) -> None:
        """
        Close connection to Juniper device.
        """
        if self._junos_device is not None:
            try:
                hostname = self._junos_device.hostname
                self._junos_device.close()
                self._junos_device = None
                logger.info(f"Connection to {hostname} closed")
            except Exception as e:
                logger.error(f"Error closing Junos connection: {e}")
        else:
            logger.warning("No active Junos connection to close")

    def connect_junos_shell(self) -> Optional[StartShell]:
        """
        Connect to Junos device shell mode.

        Returns:
            StartShell: Shell session object

        Example:
            #>>> utils = NwUtilities(hostname='device.example.com', ...)
            #>>> with utils.connect_junos_shell() as shell:
            ...     status, output = shell.run('ls -la /var/tmp')
            ...     print(output)
        """
        try:
            dev = self.junos_open_connection()
            shell = StartShell(dev)
            logger.info(f"Connected to shell mode of {dev.hostname}")
            return shell
        except Exception as e:
            logger.error(f"Failed to start shell session: {e}")
            raise

    # ==========================================
    # Jumphost Connection Methods
    # ==========================================

    def jumphost_connect(self,
                         hostname: Optional[str] = None,
                         username: Optional[str] = None,
                         password: Optional[str] = None,
                         port: Optional[int] = 22
                         ) -> SSHClient:
        """
        Establish SSH connection to jumphost.

        Returns:
            SSHClient: Connected SSH client

        Raises:
            AuthenticationException: If authentication fails
            SSHException: If SSH connection fails
        """
        if self._jumphost_client is not None:
            logger.info("Jumphost connection already open")
            return self._jumphost_client

        try:
            logger.info(f"Connecting to jumphost: {username}@{hostname}:{port}")

            jumphost_client = SSHClient()
            jumphost_client.load_system_host_keys()
            jumphost_client.set_missing_host_key_policy(AutoAddPolicy())

            jumphost_client.connect(
                hostname=hostname,
                username=username,
                password=password,
                port=port
            )

            self._jumphost_client = jumphost_client
            logger.info("Successfully connected to jumphost")

            return jumphost_client

        except AuthenticationException as e:
            logger.error(f"Authentication failed for jumphost: {e}")
            raise
        except SSHException as e:
            logger.error(f"SSH connection failed to jumphost: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error connecting to jumphost: {e}")
            raise

    def jumphost_disconnect(self) -> None:
        """
        Close jumphost SSH connection.
        """
        if self._jumphost_client is not None:
            try:
                self._jumphost_client.close()
                self._jumphost_client = None
                logger.info("Jumphost connection closed")
            except Exception as e:
                logger.error(f"Error closing jumphost connection: {e}")
        else:
            logger.warning("No active jumphost connection to close")

    def jumphost_transport_connect(self,
                                   hostname: Optional[str] = None,
                                   username: Optional[str] = None,
                                   password: Optional[str] = None,
                                   port: Optional[int] = 22,
                                   dst_host: Optional[str] = None,
                                   dst_username: Optional[str] = None,
                                   dst_password: Optional[str] = None,
                                   dst_port: Optional[int] = 22
                                   ) -> Tuple[SSHClient, SSHClient]:

        """
        Connect to a device through a jumphost using SSH tunneling.

        This creates an SSH tunnel through the jumphost to reach the target device.

        Returns:
            Tuple[SSHClient, SSHClient]: (target_client, jumphost_client)

        Raises:
            ValueError: If dst_host is not set
            SSHException: If connection fails

        Example:
            #>>> utils = NwUtilities(
            ...     hostname='jumphost.example.com',
            ...     dst_host='target.example.com',
            ...     username='admin',
            ...     password='password'
            ... )
            #>>> target, jumphost = utils.jumphost_transport_connect()
            #>>> stdin, stdout, stderr = target.exec_command('hostname')
            #>>> print(stdout.read().decode())
        """
        if not dst_host:
            raise ValueError("dst_host must be set for jumphost transport connection")

        if self._target_client is not None and self._jumphost_client is not None:
            logger.info("Jumphost transport connection already open")
            return self._target_client, self._jumphost_client
        try:
            # Connect to jumphost
            logger.info(f"Connecting to jumphost: {username}@{hostname}:{port}")

            jumphost = SSHClient()
            jumphost.load_system_host_keys()
            jumphost.set_missing_host_key_policy(AutoAddPolicy())
            jumphost.connect(
                hostname=hostname,
                username=username,
                password=password,
                port=port
            )

            logger.info("Jumphost connected, creating tunnel to target device")

            # Create tunnel
            jumpbox_transport = jumphost.get_transport()
            src_address = (hostname, port)
            dest_address = (dst_host, dst_port)

            jumpbox_channel = jumpbox_transport.open_channel(
                "direct-tcpip",
                dest_addr=dest_address,
                src_addr=src_address
            )

            # Connect to target through tunnel
            logger.info(f"Connecting to target device: {dst_host}")

            target = SSHClient()
            target.set_missing_host_key_policy(AutoAddPolicy())
            target.connect(
                hostname=dst_host,
                username=dst_username,
                password=dst_password,
                port=dst_port,
                sock=jumpbox_channel
            )

            self._target_client = target
            self._jumphost_client = jumphost

            logger.info(f"Successfully connected to target device: {dst_host}")

            return target, jumphost

        except Exception as e:
            logger.error(f"Failed to establish jumphost transport connection: {e}")
            # Clean up on failure
            if 'target' in locals():
                target.close()
            if 'jumphost' in locals():
                jumphost.close()
            raise

    def jumphost_transport_disconnect(self) -> None:
        """
        Close jumphost transport connection (both target and jumphost).
        """
        if self._target_client is not None:
            try:
                self._target_client.close()
                self._target_client = None
                logger.info("Target connection closed")
            except Exception as e:
                logger.error(f"Error closing target connection: {e}")

        if self._jumphost_client is not None:
            try:
                self._jumphost_client.close()
                self._jumphost_client = None
                logger.info("Jumphost connection closed")
            except Exception as e:
                logger.error(f"Error closing jumphost connection: {e}")

    # ==========================================
    # File System Methods
    # ==========================================

    def check_directory_exists(self, directory_path: Optional[str] = None) -> bool:
        """
        Check if a local directory exists.

        Args:
            directory_path: Path to check (uses self.directory_path if not provided)

        Returns:
            bool: True if directory exists
        """
        path = directory_path

        if not path:
            logger.error("No directory path provided")
            return False

        exists = os.path.isdir(path)

        if exists:
            logger.info(f"Directory exists: {path}")
        else:
            logger.warning(f"Directory does not exist: {path}")

        return exists

    def check_file_exists(self, filename: Optional[str] = None) -> bool:
        """
        Check if a local file exists.

        Args:
            filename: Filename to check (uses self.filename if not provided)

        Returns:
            bool: True if file exists
        """
        file = filename

        if not file:
            logger.error("No filename provided")
            return False

        exists = os.path.isfile(file)

        if exists:
            logger.info(f"File exists: {file}")
        else:
            logger.warning(f"File does not exist: {file}")

        return exists

    def create_directory(self, directory_path: Optional[str] = None) -> bool:
        """
        Create a directory if it doesn't exist.

        Args:
            directory_path: Path to create

        Returns:
            bool: True if successful
        """
        path = directory_path

        if not path:
            logger.error("No directory path provided")
            return False

        try:
            Path(path).mkdir(parents=True, exist_ok=True)
            logger.info(f"Directory created/verified: {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to create directory {path}: {e}")
            return False

    # ==========================================
    # File Transfer Methods
    # ==========================================

    def copy_file_local_to_remote(
            self,
            src_path: Optional[str] = None,
            dst_path: Optional[str] = None,
            use_jumphost: bool = True
    ) -> bool:
        """
        Copy file from local machine to remote device.

        Args:
            src_path: Source file path (local)
            dst_path: Destination file path (remote)
            use_jumphost: Whether to use jumphost connection

        Returns:
            bool: True if successful

        Raises:
            FileNotFoundError: If source file doesn't exist
        """
        source = src_path
        destination = dst_path

        if not source or not destination:
            logger.error("Source and destination paths must be provided")
            return False

        if not os.path.exists(source):
            raise FileNotFoundError(f"Source file not found: {source}")

        try:
            if use_jumphost:
                logger.info(f"Copying {source} to {destination} via jumphost")
                jumphost = self.jumphost_connect()

                with SCPClient(jumphost.get_transport()) as scp:
                    scp.put(source, destination)

            else:
                logger.error("Direct SCP not implemented. Use use_jumphost=True")
                return False

            logger.info(f"Successfully copied {source} to {destination}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            raise

    def copy_file_remote_to_local(
            self,
            src_path: Optional[str] = None,
            dst_path: Optional[str] = None,
            use_jumphost: bool = True
    ) -> bool:
        """
        Copy file from remote device to local machine.

        Args:
            src_path: Source file path (remote)
            dst_path: Destination file path (local)
            use_jumphost: Whether to use jumphost connection

        Returns:
            bool: True if successful
        """
        source = src_path
        destination = dst_path

        if not source or not destination:
            logger.error("Source and destination paths must be provided")
            return False

        try:
            if use_jumphost:
                logger.info(f"Copying {source} from remote to {destination}")
                jumphost = self.jumphost_connect()

                with SCPClient(jumphost.get_transport()) as scp:
                    scp.get(source, destination)

            else:
                logger.error("Direct SCP not implemented. Use use_jumphost=True")
                return False

            logger.info(f"Successfully copied {source} to {destination}")
            return True

        except Exception as e:
            logger.error(f"Failed to copy file: {e}")
            raise

    # ==========================================
    # Email Methods
    # ==========================================

    def send_email(
            self,
            email_from: Optional[str] = None,
            email_to: Optional[str] = None,
            email_subject: Optional[str] = None,
            email_body: Optional[str] = None,
            greeting: Optional[str] = None,
            cc_emails: Optional[List[str]] = None,
            destination_path: Optional[str] = None,
            attach_list: Optional[List[str]] = None,
            smtp_server: str = 'localhost',
            smtp_port: int = 25
    ) -> bool:
        """
        Send an email with optional attachments.

        Args:
            email_from: Sender email address
            email_to: Recipient email address
            email_subject: Email subject
            email_body: Email body content
            greeting: Email greeting
            cc_emails: List of CC email addresses
            destination_path: Path to attachment directory
            attach_list: List of attachment filenames
            smtp_server: SMTP server address
            smtp_port: SMTP server port

        Returns:
            bool: True if successful

        Raises:
            ValueError: If required parameters are missing
        """
        # Use provided parameters or fall back to instance attributes
        from_addr = email_from
        to_addr = email_to
        subject = email_subject
        body = email_body
        greet = greeting
        cc_list = cc_emails
        attach_path = destination_path
        attachments = attach_list

        # Validate required parameters
        if not all([from_addr, to_addr, subject, greet, body]):
            missing = [
                param for param, value in {
                    'email_from': from_addr,
                    'email_to': to_addr,
                    'email_subject': subject,
                    'greeting': greet,
                    'email_body': body
                }.items() if not value
            ]
            raise ValueError(f"Missing required email parameters: {', '.join(missing)}")

        try:
            logger.info(f"Preparing email to {to_addr}")

            # Create message
            msg = MIMEMultipart()
            msg['Date'] = datetime.now().strftime('%a, %d %b %Y %H:%M:%S %z')
            msg['From'] = from_addr
            msg['To'] = to_addr
            msg['Subject'] = subject

            # Add CC recipients
            if cc_list:
                msg['Cc'] = ', '.join(cc_list)

            # Get email footer from config
            email_footer = self._get_config('email_data', 'email_footer', '')

            # Create HTML body
            html = f"""\
            <html>
                <head>
                    <meta charset="UTF-8">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            line-height: 1.6;
                            color: #333333;
                        }}
                    </style>
                </head>
                <body>
                    <p>{greet}</p>
                    <p>{body}</p>
                    <p></p>
                    <p>- Grasshopper Automation</p>
                    {f'<p>- {email_footer}</p>' if email_footer else ''}
                </body>
            </html>
            """

            msg.attach(MIMEText(html, 'html'))

            # Attach files if provided
            if attachments and attach_path:
                logger.info(f"Attaching {len(attachments)} file(s)")

                for filename in attachments:
                    file_path = os.path.join(attach_path, filename)

                    if not os.path.exists(file_path):
                        logger.warning(f"Attachment not found: {file_path}")
                        continue

                    with open(file_path, 'rb') as f:
                        attachment = MIMEApplication(f.read(), _subtype='txt')
                        attachment.add_header(
                            'Content-Disposition',
                            'attachment',
                            filename=filename
                        )
                        msg.attach(attachment)

                    logger.debug(f"Attached: {filename}")

            # Send email
            logger.info(f"Sending email via {smtp_server}:{smtp_port}")

            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.send_message(msg)

            logger.info(f"Email sent successfully to {to_addr}")
            print(f"✓ Email sent to {to_addr}")

            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise

    # ==========================================
    # Context Manager Support
    # ==========================================

    def __enter__(self):
        """Support for context manager (with statement)"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up connections on exit"""
        self.close_all_connections()

    def close_all_connections(self) -> None:
        """
        Close all active connections.
        """
        logger.info("Closing all connections")

        self.junos_close_connection()
        self.jumphost_transport_disconnect()
        self.jumphost_disconnect()

        logger.info("All connections closed")
