"""
FTP client for downloading XLSX files from remote server
Adapted from west_fin project for fin module
"""
import os
import logging
from ftplib import FTP
from typing import List, Tuple
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class FinFTPClient:
    """FTP client for file operations - fin module"""

    def __init__(self):
        self.host = settings.FTP_HOST
        self.port = settings.FTP_PORT
        self.user = settings.FTP_USER
        self.password = settings.FTP_PASSWORD
        self.remote_dir = settings.FTP_DIRECTORY
        self.local_dir = Path(settings.FTP_DOWNLOAD_DIR)
        self.ftp = None

    def connect(self) -> bool:
        """
        Connect to FTP server

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            self.ftp = FTP()
            self.ftp.connect(self.host, self.port)
            self.ftp.login(self.user, self.password)
            self.ftp.encoding = 'utf-8'
            logger.info(f"Connected to FTP server: {self.host}")
            return True
        except Exception as e:
            logger.error(f"FTP connection failed: {e}")
            return False

    def disconnect(self):
        """Disconnect from FTP server"""
        if self.ftp:
            try:
                self.ftp.quit()
                logger.info("Disconnected from FTP server")
            except Exception as e:
                logger.warning(f"FTP disconnect warning: {e}")

    def list_xlsx_files(self) -> List[str]:
        """
        List all XLSX files in remote directory

        Returns:
            List[str]: List of XLSX filenames
        """
        if not self.ftp:
            logger.error("Not connected to FTP server")
            return []

        try:
            # Change to remote directory
            self.ftp.cwd(self.remote_dir)

            # Get list of files
            files = self.ftp.nlst()

            # Filter XLSX files
            xlsx_files = [
                f for f in files
                if f.lower().endswith(('.xlsx', '.xls'))
            ]

            logger.info(f"Found {len(xlsx_files)} XLSX files on FTP server")
            return xlsx_files

        except Exception as e:
            logger.error(f"Error listing FTP files: {e}")
            return []

    def download_file(self, remote_filename: str) -> Tuple[bool, str]:
        """
        Download a single file from FTP server

        Args:
            remote_filename: Name of file to download

        Returns:
            Tuple[bool, str]: (Success status, Local file path)
        """
        if not self.ftp:
            logger.error("Not connected to FTP server")
            return False, ""

        try:
            # Ensure local directory exists
            self.local_dir.mkdir(parents=True, exist_ok=True)

            # Construct local file path
            local_path = self.local_dir / remote_filename

            # Download file
            with open(local_path, 'wb') as local_file:
                self.ftp.retrbinary(f'RETR {remote_filename}', local_file.write)

            file_size = local_path.stat().st_size
            logger.info(
                f"Downloaded: {remote_filename} "
                f"({file_size / 1024:.1f} KB)"
            )

            return True, str(local_path)

        except Exception as e:
            logger.error(f"Error downloading {remote_filename}: {e}")
            return False, ""

    def download_all_xlsx(self) -> List[str]:
        """
        Download all XLSX files from FTP server

        Returns:
            List[str]: List of downloaded file paths
        """
        downloaded_files = []

        if not self.connect():
            return downloaded_files

        try:
            xlsx_files = self.list_xlsx_files()

            for filename in xlsx_files:
                success, local_path = self.download_file(filename)
                if success:
                    downloaded_files.append(local_path)

            logger.info(
                f"Downloaded {len(downloaded_files)} files "
                f"from FTP server"
            )

        except Exception as e:
            logger.error(f"Error during FTP download: {e}")

        finally:
            self.disconnect()

        return downloaded_files


def download_ftp_files() -> List[str]:
    """
    Convenience function to download all XLSX files from FTP

    Returns:
        List[str]: List of downloaded file paths
    """
    client = FinFTPClient()
    return client.download_all_xlsx()
