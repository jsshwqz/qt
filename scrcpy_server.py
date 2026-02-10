#!/usr/bin/env python3
import subprocess, time, os
from adb_manager import get_resource_path

class ScrcpyServerManager:
    def __init__(self, device_id, adb_manager):
        self.device_id = device_id
        self.adb_manager = adb_manager
        self.server_process = None

    def _adb_executable(self):
        # support both attribute names used in repo
        return getattr(self.adb_manager, 'adb_path', getattr(self.adb_manager, 'path', 'adb'))

    def start_server(self, version='3.3.3'):
        # 确保 JAR 已推送（从打包资源或当前目录读取）
        local_jar = get_resource_path('scrcpy-server.jar')
        adb = self._adb_executable()
        subprocess.run([adb, '-s', self.device_id, 'push', local_jar, '/data/local/tmp/scrcpy-server.jar'], 
                      capture_output=True, creationflags=0x08000000)
        time.sleep(1)

        # 使用匹配的 server 版本启动
        cmd_str = f"CLASSPATH=/data/local/tmp/scrcpy-server.jar app_process / com.genymobile.scrcpy.Server {version} tunnel_forward=true log_level=info video=true audio=false control=true max_size=1080"
        cmd = [adb, '-s', self.device_id, 'shell', cmd_str]

        try:
            self.server_process = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT, 
                universal_newlines=True,
                creationflags=0x08000000
            )
            time.sleep(2)  # 等待服务启动
            return True
        except Exception as e:
            print(f'Failed to start Scrcpy Server: {e}')
            return False

    def setup_port_forwarding(self, local_port=27183):
        return self.adb_manager.forward_port(self.device_id, local_port, local_port)

    def stop_server(self):
        if self.server_process:
            try:
                self.server_process.terminate()
            except:
                pass
