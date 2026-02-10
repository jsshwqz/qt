#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ADB (Android Debug Bridge) Management Module

This module provides the AdbServerManager class to handle ADB operations,
including starting the server, listing connected devices, and port forwarding.
Refactored to use unified logging and exception handling.
"""

import subprocess
import os
import sys
import logging
from typing import List, Optional

from exceptions import (
    AdbException, 
    DeviceNotFoundException, 
    wrap_exception
)
from log_manager import get_logger

# Initialize logger using the unified log manager
logger = get_logger()


def get_resource_path(relative_path: str) -> str:
    """
    Get the absolute path to a resource file.
    Works for both development and PyInstaller bundled environments.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


class AdbServerManager:
    """Manager class for ADB server operations."""

    def __init__(self, adb_exe_path: Optional[str] = None):
        """
        Initialize the ADB server manager.
        
        Args:
            adb_exe_path: Optional custom path to adb.exe. If not provided,
                         it will search in standard locations.
        """
        self.adb_path = adb_exe_path or self._find_adb_path()
        logger.info(f"AdbServerManager initialized. ADB Path: {self.adb_path}")

    @staticmethod
    def _find_adb_path() -> str:
        """
        Search for adb.exe in standard locations.
        
        Search order:
        1. Current working directory.
        2. Script directory.
        3. Local platform-tools path.
        4. System PATH.
        
        Returns:
            The absolute path to adb.exe or 'adb' as fallback.
        """
        # 1. Check current directory
        if os.path.exists("adb.exe"):
            return os.path.abspath("adb.exe")

        # 2. Check script directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        script_adb = os.path.join(script_dir, "adb.exe")
        if os.path.exists(script_adb):
            return script_adb

        # 3. Dedicated known local paths
        known_paths = [
            r"E:\Program Files\platform-tools\adb.exe",
            r"E:\Program Files\qt\QtScrcpy-Release\QtScrcpy-win-x64-v3.3.3\adb.exe"
        ]
        for path in known_paths:
            if os.path.exists(path):
                return path

        # 4. Fallback to 'adb' in PATH
        logger.debug("adb.exe not found in local paths, falling back to system PATH")
        return "adb"

    @wrap_exception
    def start_server(self) -> bool:
        """
        Ensure the ADB server is running.
        
        Returns:
            True if started or already running, False otherwise.
        
        Raises:
            AdbException: If ADB server fails to start.
        """
        try:
            # Use CREATE_NO_WINDOW (0x08000000) for Windows to prevent CMD flicker
            creation_flags = 0x08000000 if os.name == 'nt' else 0
            
            process = subprocess.run(
                [self.adb_path, "start-server"],
                capture_output=True,
                creationflags=creation_flags,
                timeout=15
            )
            if process.returncode == 0:
                logger.info("ADB server started successfully.")
                return True
            else:
                err = process.stderr.decode(errors='ignore').strip()
                logger.error(f"Failed to start ADB server: {err}")
                raise AdbException(f"Failed to start ADB server: {err}")
                
        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.error(f"Subprocess error starting ADB server: {e}")
            raise AdbException(f"Subprocess error starting ADB server: {e}")

    @wrap_exception
    def list_devices(self) -> List[str]:
        """
        Get a list of currently connected Android devices.
        
        Returns:
            A list of device serial numbers.
        """
        try:
            creation_flags = 0x08000000 if os.name == 'nt' else 0
            
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                creationflags=creation_flags,
                timeout=10
            )

            if result.returncode != 0:
                logger.warning(f"ADB 'devices' command failed: {result.stderr}")
                raise AdbException(f"ADB 'devices' command failed: {result.stderr}")

            devices = []
            lines = result.stdout.strip().splitlines()
            if len(lines) > 1:
                # Skip the first head line "List of devices attached"
                for line in lines[1:]:
                    if not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == 'device':
                        devices.append(parts[0])

            logger.debug(f"Detected {len(devices)} device(s): {devices}")
            return devices
            
        except Exception as e:
            logger.error(f"Error listing devices: {e}")
            raise AdbException(f"Error listing devices: {e}")

    @wrap_exception
    def forward_port(self, serial: str, local_port: int, remote_abstract: str) -> bool:
        """
        Setup port forwarding for the device.
        Usually used for Scrcpy control/video sockets.
        
        Args:
            serial: Device serial number.
            local_port: Port number on the PC.
            remote_abstract: Abstract name on the Android device (e.g. 'localabstract:scrcpy').
        
        Returns:
            True if successful.
        """
        try:
            creation_flags = 0x08000000 if os.name == 'nt' else 0
            
            cmd = [self.adb_path, "-s", serial, "forward", f"tcp:{local_port}", remote_abstract]
            result = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=creation_flags,
                timeout=10
            )
            if result.returncode == 0:
                logger.info(f"Port forwarding established: {local_port} -> {remote_abstract}")
                return True
            else:
                err = result.stderr.decode(errors='ignore').strip()
                msg = f"Failed to forward port: {err}"
                logger.error(msg)
                raise AdbException(msg)
                
        except Exception as e:
            logger.error(f"Error setting up port forwarding: {e}")
            raise AdbException(f"Error setting up port forwarding: {e}")

    def remove_forward(self, local_port: int):
        """Remove a specific port forwarding."""
        try:
            creation_flags = 0x08000000 if os.name == 'nt' else 0
            
            subprocess.run(
                [self.adb_path, "forward", "--remove", f"tcp:{local_port}"],
                creationflags=creation_flags,
                timeout=5
            )
            logger.info(f"Port forwarding removed: {local_port}")
        except Exception as e:
            logger.debug(f"Failed to remove port forward {local_port} (expected if already gone): {e}")

    @property
    def path(self) -> str:
        """Return the used ADB path."""
        return self.adb_path


if __name__ == "__main__":
    # Self-test
    try:
        manager = AdbServerManager()
        if manager.start_server():
            print(f"Connected devices: {manager.list_devices()}")
        else:
            print("Failed to start ADB server.")
    except Exception as e:
        print(f"Error: {e}")