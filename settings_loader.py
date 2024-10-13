import json
import os
from typing import Optional

from settings import GlobalSettings


class SettingsLoader:
    def __init__(self):
        # Interface implementation
        pass

    def touch(self) -> Exception:
        raise NotImplementedError()

    def load(self) -> Exception:
        raise NotImplementedError()

    def save(self) -> Exception:
        raise NotImplementedError()

    def get_settings(self) -> Optional[GlobalSettings]:
        raise NotImplementedError()


class FileSettingsLoader(SettingsLoader):
    config_path = None

    _settings: Optional[GlobalSettings] = None

    def __init__(self, config_path: str):
        SettingsLoader.__init__(self)
        self.config_path = config_path

    def touch(self) -> Exception:
        config_file_exists = os.path.exists(self.config_path)
        is_config_path_file = os.path.isfile(self.config_path)
        if not config_file_exists or not is_config_path_file:
            try:
                with open(self.config_path, "w") as config_write:
                    config_write.write("{}")
            except Exception as e:
                return e

        return None

    def load(self) -> Exception:
        global_settings_dict = None

        try:
            with open(self.config_path, "r") as config_read:
                global_settings_dict = json.load(config_read)
        except Exception as e:
            return e

        self._settings = GlobalSettings(global_settings_dict)

        return None

    def save(self) -> Exception:
        if self._settings is None:
            return Exception("settings are not loaded")

        global_settings_dict = self._settings.get_dict()

        try:
            with open(self.config_path, "w") as config_write:
                json.dump(global_settings_dict, config_write)
        except Exception as e:
            return e

        return None

    def get_settings(self) -> Optional[GlobalSettings]:
        return self._settings
