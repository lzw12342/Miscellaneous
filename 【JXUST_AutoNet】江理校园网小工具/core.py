import configparser
import subprocess
import time
import requests
import threading
import platform
import sys  # 新增：修复sys未定义错误
from typing import Optional, Tuple, List, Dict, Any
from dataclasses import dataclass, asdict
import winreg
from ctypes import windll

# Logger全局变量
logger = None

def set_logger(custom_logger):
    """设置GUI传来的logger实例"""
    global logger
    logger = custom_logger

# ==================== 配置数据类 ====================

@dataclass
class UserConfig:
    """用户配置"""
    username: str = ""
    password: str = ""
    provider: str = "telecom"  # "telecom"/"cmcc"/"unicom"

@dataclass
class SettingConfig:
    """高级设置配置"""
    interval: int = 30  # 检查间隔秒数
    host: str = "www.qq.com"  # 用于ping检测的目标主机
    wifi_ssid: str = "JXUST-WLAN"  # WiFi SSID
    autostart: bool = False  # 新增：开机自启动

# ==================== 配置管理器 ====================

class ConfigManager:
    """管理配置文件的User和Setting两个section"""
    
    USER_SECTION = 'User'
    SETTING_SECTION = 'Setting'
    
    def __init__(self, config_file: str = 'config.ini'):
        self.config_file = config_file
        self.config = configparser.ConfigParser()
        
        # 定义各section的字段
        self.user_fields = {
            'username': '',
            'password': '',
            'provider': 'telecom'
        }
        
        self.setting_fields = {
            'interval': '30',
            'host': 'www.qq.com',
            'wifi_ssid': 'JXUST-WLAN',
            'autostart': 'false'  # 新增
        }

    def load(self) -> Tuple[Optional[UserConfig], Optional[SettingConfig], Dict[str, List[str]]]:
        """加载配置，返回(用户配置, 设置配置, 缺失字段)"""
        missing_fields = {self.USER_SECTION: [], self.SETTING_SECTION: []}
        
        try:
            self.config.read(self.config_file, encoding='utf-8')
            
            # 加载User配置
            user_config = UserConfig()
            if self.config.has_section(self.USER_SECTION):
                for field, default in self.user_fields.items():
                    if self.config.has_option(self.USER_SECTION, field):
                        setattr(user_config, field, self.config.get(self.USER_SECTION, field))
                    else:
                        missing_fields[self.USER_SECTION].append(field)
            else:
                missing_fields[self.USER_SECTION] = list(self.user_fields.keys())
            
            # 加载Setting配置
            setting_config = SettingConfig()
            if self.config.has_section(self.SETTING_SECTION):
                for field, default in self.setting_fields.items():
                    if self.config.has_option(self.SETTING_SECTION, field):
                        # 特殊处理interval为整数
                        if field == 'interval':
                            setattr(setting_config, field, self.config.getint(self.SETTING_SECTION, field))
                        else:
                            setattr(setting_config, field, self.config.get(self.SETTING_SECTION, field))
                    else:
                        missing_fields[self.SETTING_SECTION].append(field)
            else:
                missing_fields[self.SETTING_SECTION] = list(self.setting_fields.keys())
            
            if logger:
                logger.debug(f"配置加载: User={user_config}, Setting={setting_config}")
            
            # 如果某section完全缺失，返回None
            user_config = None if missing_fields[self.USER_SECTION] == list(self.user_fields.keys()) else user_config
            setting_config = None if missing_fields[self.SETTING_SECTION] == list(self.setting_fields.keys()) else setting_config
            
            return user_config, setting_config, missing_fields
            
        except Exception as e:
            if logger:
                logger.error(f"加载配置文件出错: {e}")
            return None, None, {self.USER_SECTION: list(self.user_fields.keys()), 
                               self.SETTING_SECTION: list(self.setting_fields.keys())}

    def save(self, user_config: Optional[UserConfig] = None, 
             setting_config: Optional[SettingConfig] = None) -> bool:
        """保存配置到文件"""
        try:
            # 确保sections存在
            if not self.config.has_section(self.USER_SECTION):
                self.config.add_section(self.USER_SECTION)
            if not self.config.has_section(self.SETTING_SECTION):
                self.config.add_section(self.SETTING_SECTION)
            
            # 保存User配置
            if user_config:
                for field, default in self.user_fields.items():
                    value = getattr(user_config, field, default)
                    self.config.set(self.USER_SECTION, field, str(value))
            
            # 保存Setting配置
            if setting_config:
                for field, default in self.setting_fields.items():
                    value = getattr(setting_config, field, default)
                    self.config.set(self.SETTING_SECTION, field, str(value))
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                self.config.write(f)
            
            if logger:
                logger.info("配置保存成功")
            return True
            
        except Exception as e:
            if logger:
                logger.error(f"保存配置失败: {e}")
            return False

# ==================== 网络管理器 ====================

class NetworkManager:
    """处理WiFi连接和网络检测的核心逻辑"""
    
    AUTH_URL = "http://eportal.jxust.edu.cn:801/eportal/portal/login"
    AUTH_HEADERS = {
        'Host': 'eportal.jxust.edu.cn:801',
        'Referer': 'http://eportal.jxust.edu.cn/',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    def __init__(self, user_config: UserConfig, setting_config: SettingConfig):
        self.user_config = user_config
        self.setting_config = setting_config
        self._stop_event = threading.Event()
        self._monitor_thread = None
        self._last_check_time = 0
        self._check_interval = setting_config.interval
        
        # Windows下隐藏控制台窗口
        self.startupinfo = None
        if platform.system() == "Windows":
            self.startupinfo = subprocess.STARTUPINFO()
            self.startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.startupinfo.wShowWindow = subprocess.SW_HIDE

    def connect_wifi(self) -> bool:
        """连接指定WiFi（静默模式）"""
        try:
            if logger:
                logger.info(f"尝试连接WiFi: {self.setting_config.wifi_ssid}")
            
            # 断开当前连接
            subprocess.run(
                ['netsh', 'wlan', 'disconnect'],
                capture_output=True,
                text=True,
                timeout=5,
                startupinfo=self.startupinfo  # 隐藏窗口
            )
            
            # 连接目标WiFi
            result = subprocess.run(
                ['netsh', 'wlan', 'connect', f'name={self.setting_config.wifi_ssid}'],
                capture_output=True,
                text=True,
                timeout=30,
                startupinfo=self.startupinfo  # 隐藏窗口
            )
            
            if result.returncode == 0:
                time.sleep(2)
                if self._verify_wifi_connected():
                    if logger:
                        logger.info("WiFi连接成功")
                    return True
                else:
                    if logger:
                        logger.error("WiFi连接后验证失败")
                    return False
            else:
                if logger:
                    logger.error(f"WiFi连接失败: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            if logger:
                logger.error("WiFi连接超时")
            return False
        except Exception as e:
            if logger:
                logger.error(f"WiFi连接异常: {e}", exc_info=True)
            return False

    def _verify_wifi_connected(self) -> bool:
        """验证WiFi连接状态"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True,
                timeout=5,
                startupinfo=self.startupinfo  # 隐藏窗口
            )
            return self.setting_config.wifi_ssid in result.stdout and "已连接" in result.stdout
        except:
            return False

    def check_internet_connectivity(self) -> bool:
        """静默检测网络连通性"""
        current_time = time.time()
        if current_time - self._last_check_time < 1.0:
            return True
        
        self._last_check_time = current_time
        
        system = platform.system().lower()
        
        try:
            if system == "windows":
                cmd = ["ping", "-n", "1", "-w", "2000", self.setting_config.host]
            else:
                cmd = ["ping", "-c", "1", "-W", "2", self.setting_config.host]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                startupinfo=self.startupinfo  # 隐藏窗口
            )
            success = result.returncode == 0
            
            if not success and logger:
                logger.debug(f"Ping {self.setting_config.host} 失败")
            
            return success
                
        except Exception as e:
            if logger:
                logger.debug(f"Ping检测异常: {e}")
            return False

    def authenticate(self) -> bool:
        """Portal认证（带重试）"""
        max_retries = 2
        retry_delay = 3
        
        for attempt in range(max_retries):
            try:
                if logger:
                    logger.info(f"尝试Portal认证 (第 {attempt + 1}/{max_retries} 次)...")
                
                params = {
                    'callback': 'dr1003',
                    'login_method': '1',
                    'user_account': f"{self.user_config.username}@{self.user_config.provider}",
                    'user_password': self.user_config.password,
                }
                
                response = requests.get(
                    self.AUTH_URL,
                    params=params,
                    headers=self.AUTH_HEADERS,
                    timeout=10
                )
                
                response_text = response.text
                if logger:
                    logger.debug(f"认证响应: {response_text[:100]}...")
                
                # 统一处理逻辑：只要包含"在线"就视为成功
                is_success = False
                is_online = False
                
                # 解析JSONP响应
                if response_text.startswith('dr1003('):
                    json_str = response_text[7:].rstrip(');')
                    try:
                        import json
                        result_data = json.loads(json_str)
                        result_code = result_data.get('result')
                        msg = result_data.get('msg', '')
                        
                        # 判断成功或在线
                        if result_code == 1:
                            is_success = True
                        elif result_code == 0:
                            # 关键修复：检查是否包含"在线"（兼容"已在线"和"已经在线"）
                            if "在线" in msg:
                                is_online = True
                            else:
                                # 其他情况才是真正失败
                                if logger:
                                    logger.warning(f"认证失败: {msg}")
                                continue  # 继续重试
                    except json.JSONDecodeError:
                        # JSON解析失败，降级到文本匹配
                        if logger:
                            logger.warning("JSON解析失败，使用文本匹配")
                        pass
                
                # 文本匹配兜底（针对所有情况）
                if "result=1" in response_text or "success" in response_text.lower():
                    is_success = True
                elif "在线" in response_text:  # 关键修复：模糊匹配所有"在线"情况
                    is_online = True
                
                # 最终判断
                if is_success:
                    if logger:
                        logger.info("Portal认证成功")
                    time.sleep(2)
                    return True
                elif is_online:
                    if logger:
                        logger.info("用户已在线，认证跳过")
                    time.sleep(1)
                    return True  # 关键：立即返回True
                
                # 如果走到这里，说明确实失败了
                if attempt < max_retries - 1:
                    if logger:
                        logger.info(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                    continue
                else:
                    if logger:
                        logger.error("认证失败，已达到最大重试次数")
                    return False
                        
            except Exception as e:
                if logger:
                    logger.error(f"认证异常 (第 {attempt + 1}/{max_retries} 次): {e}")
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
                    continue
        return False

    def start_monitoring(self):
        """启动后台监控线程"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            if logger:
                logger.warning("监控线程已在运行")
            return
        
        if logger:
            logger.info(f"启动网络监控，间隔 {self.setting_config.interval} 秒")
        self._stop_event.clear()
        
        def monitor_loop():
            consecutive_failures = 0
            max_failures = 3
            check_count = 0
            
            while not self._stop_event.wait(self.setting_config.interval):
                try:
                    check_count += 1
                    is_connected = self.check_internet_connectivity()
                    
                    if not is_connected:
                        consecutive_failures += 1
                        # 只有第一次失败时记录日志
                        if consecutive_failures == 1:
                            if logger:
                                logger.debug(f"Ping {self.setting_config.host} 失败 (第 1/{max_failures} 次)")
                        elif logger:
                            logger.debug(f"Ping {self.setting_config.host} 失败 (第 {consecutive_failures}/{max_failures} 次)")
                        
                        # 只有达到阈值时才 WARNING 并重连
                        if consecutive_failures >= max_failures:
                            if logger:
                                logger.warning(f"连续 {max_failures} 次检查失败，尝试重新连接WiFi...")
                            
                            # 重新连接WiFi
                            if self.connect_wifi():
                                if logger:
                                    logger.info("WiFi重连成功，尝试认证...")
                            else:
                                if logger:
                                    logger.error("WiFi重连失败")
                            
                            # 执行认证
                            if self.authenticate():
                                consecutive_failures = 0
                                if logger:
                                    logger.info("认证成功，网络恢复")
                            else:
                                if logger:
                                    logger.error("认证失败，稍后重试")
                    else:
                        if consecutive_failures > 0:
                            if logger:
                                logger.info("网络连接恢复")
                        consecutive_failures = 0
                        
                        # 每10次检查记录一次DEBUG日志
                        if check_count % 10 == 0:
                            if logger:
                                logger.debug("网络连接正常")
                        
                except Exception as e:
                    if logger:
                        logger.error(f"监控循环异常: {e}")
                    consecutive_failures += 1
        
        self._monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self._monitor_thread.start()
        if logger:
            logger.info("监控线程已启动")

    def stop_monitoring(self):
        """停止监控"""
        if not self._monitor_thread:
            return
            
        if logger:
            logger.info("正在停止监控...")
        self._stop_event.set()

# ==================== 主控制器 ====================

class AutoConnectMachine:
    """自动连接机器：协调WiFi和认证流程"""
    
    def __init__(self, user_config: UserConfig, setting_config: SettingConfig):
        self.user_config = user_config
        self.setting_config = setting_config
        self.network_manager = NetworkManager(user_config, setting_config)
        self._stop_requested = threading.Event()
        self._is_running = False

    def run(self):
        """主运行流程"""
        if logger:
            logger.info("启动自动连接流程...")
        
        self._is_running = True
        
        # 初始连接WiFi
        if logger:
            logger.info("初始化WiFi连接...")
        
        if not self.network_manager.connect_wifi():
            if logger:
                logger.error("WiFi初始化失败")
            self._is_running = False
            return
        
        # 执行认证
        if self.network_manager.authenticate():
            if logger:
                logger.info("="*40)
                logger.info("启动成功！")
                logger.info(f"用户: {self.user_config.username}")
                logger.info(f"运营商: {self._get_provider_name()}")
                logger.info(f"检查间隔: {self.setting_config.interval}秒")
                logger.info(f"检测主机: {self.setting_config.host}")
                logger.info("="*40)
        else:
            if logger:
                logger.error("认证失败")
            self._is_running = False
            return
        
        # 启动监控
        self.network_manager.start_monitoring()
        
        # 主循环等待停止信号
        try:
            while self._is_running and not self._stop_requested.wait(1):
                time.sleep(1)
        except KeyboardInterrupt:
            if logger:
                logger.info("收到Ctrl+C，正在退出...")
        except Exception as e:
            if logger:
                logger.error(f"主循环异常: {e}", exc_info=True)
        
        if logger:
            logger.info("正在清理资源...")
        self._cleanup()

    def stop(self):
        """请求停止"""
        if logger:
            logger.info("用户请求停止程序...")
        self._stop_requested.set()
        self._is_running = False
        if self.network_manager:
            self.network_manager.stop_monitoring()

    def is_running(self) -> bool:
        return self._is_running

    def _cleanup(self):
        """清理资源"""
        if logger:
            logger.info("执行清理...")
        if self.network_manager:
            self.network_manager.stop_monitoring()
        if logger:
            logger.info("程序已退出")

    def _get_provider_name(self) -> str:
        """转换运营商代码为中文名"""
        provider_map = {
            "telecom": "电信",
            "cmcc": "移动",
            "unicom": "联通"
        }
        return provider_map.get(self.user_config.provider, "未知")
    
class SystemUtils:
    """系统工具类：处理开机自启动等系统级操作"""
    
    def __init__(self):
        self.app_name = "CampusWiFiAutoConnect"
        self.executable_path = self._get_executable_path()
        
    def _get_executable_path(self) -> str:
        """获取可执行文件完整路径"""
        if getattr(sys, 'frozen', False):
            # 如果是PyInstaller打包后的exe
            exe_path = sys.executable
        else:
            # 如果是Python脚本
            exe_path = sys.argv[0]
        
        # 返回带参数的路径（静默启动）
        return f'"{exe_path}" --minimized'
    
    def is_autostart_enabled(self) -> bool:
        """检查开机自启动是否已启用"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_READ
            )
            try:
                value, _ = winreg.QueryValueEx(key, self.app_name)
                winreg.CloseKey(key)
                return value == self.executable_path
            except FileNotFoundError:
                winreg.CloseKey(key)
                return False
        except Exception as e:
            if logger:
                logger.error(f"检查自启动状态失败: {e}")
            return False
    
    def set_autostart(self, enable: bool) -> bool:
        """启用或禁用开机自启动"""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            
            if enable:
                winreg.SetValueEx(key, self.app_name, 0, winreg.REG_SZ, self.executable_path)
                if logger:
                    logger.info("已启用开机自启动")
            else:
                winreg.DeleteValue(key, self.app_name)
                if logger:
                    logger.info("已禁用开机自启动")
            
            winreg.CloseKey(key)
            return True
            
        except PermissionError:
            if logger:
                logger.error("权限不足：需要管理员权限修改开机自启动")
            return False
        except Exception as e:
            if logger:
                logger.error(f"设置自启动失败: {e}")
            return False
    
    @staticmethod
    def is_admin() -> bool:
        """检查是否具有管理员权限"""
        try:
            return windll.shell32.IsUserAnAdmin()
        except:
            return False
    
    @staticmethod
    def run_as_admin():
        """以管理员权限重新运行程序"""
        try:
            script = sys.argv[0]
            params = " ".join([f'--{arg}' for arg in sys.argv[1:]])
            
            # 使用ShellExecute运行新实例
            windll.shell32.ShellExecuteW(
                None,
                "runas",
                sys.executable,
                f'"{script}" {params}',
                None,
                1
            )
            return True
        except Exception as e:
            if logger:
                logger.error(f"请求管理员权限失败: {e}")
            return False
