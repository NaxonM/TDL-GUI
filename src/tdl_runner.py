import urllib.request
from .worker import Worker


class TdlRunner:
    def __init__(self, tdl_path, settings_manager, logger):
        self.tdl_path = tdl_path
        self.settings_manager = settings_manager
        self.logger = logger
        self.worker = None

    def _get_proxy_args(self):
        if self.settings_manager.get("auto_proxy", True):
            proxies = urllib.request.getproxies()
            proxy = proxies.get("https", proxies.get("http"))
            if proxy:
                self.logger.debug(f"Using system proxy: {proxy}")
                return ["--proxy", proxy]
        elif self.settings_manager.get("manual_proxy", ""):
            proxy = self.settings_manager.get("manual_proxy")
            self.logger.debug(f"Using manual proxy: {proxy}")
            return ["--proxy", proxy]
        return []

    def _get_storage_args(self):
        driver = self.settings_manager.get("storage_driver", "bolt")
        path = self.settings_manager.get("storage_path", "").strip()
        if not path:
            return []
        storage_str = f"type={driver},path={path}"
        return ["--storage", storage_str]

    def _get_namespace_args(self):
        namespace = self.settings_manager.get("namespace", "default")
        if namespace and namespace != "default":
            return ["--ns", namespace]
        return []

    def _get_ntp_args(self):
        ntp_server = self.settings_manager.get("ntp_server", "").strip()
        if ntp_server:
            return ["--ntp", ntp_server]
        return []

    def _get_reconnect_timeout_args(self):
        reconnect_timeout = self.settings_manager.get("reconnect_timeout", "5m").strip()
        if (
            reconnect_timeout
            and reconnect_timeout != "5m"
            and reconnect_timeout != "0s"
        ):
            return ["--reconnect-timeout", reconnect_timeout]
        return []

    def is_running(self):
        return self.worker is not None and self.worker.isRunning()

    def stop(self):
        if self.is_running():
            self.worker.stop()

    def run(self, base_command, timeout=None):
        if self.is_running():
            self.logger.warning("A task is already running.")
            return None

        command = [self.tdl_path] + base_command

        # Add global flags
        if self.settings_manager.get("debug_mode", False):
            command.append("--debug")
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())

        self.logger.info(f"Running command: {' '.join(command)}")

        if timeout is None:
            timeout = self.settings_manager.get("command_timeout", 300)

        self.worker = Worker(command, self.logger, timeout=timeout)
        return self.worker
