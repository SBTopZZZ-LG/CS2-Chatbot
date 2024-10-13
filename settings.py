from typing import Optional


class CAISettings:
    _token: Optional[str] = None
    _token_key = "token"

    def __init__(self, cai_settings_dict: dict):
        self._token = cai_settings_dict.get(self._token_key, None)

    def get_token(self) -> Optional[str]:
        return self._token

    def set_token(self, token: Optional[str]):
        self._token = token

    def get_dict(self) -> dict:
        return {self._token_key: self._token}


class GlobalSettings:
    _cai_settings: CAISettings
    _cai_settings_key = "cai"

    def __init__(self, global_settings_dict: dict):
        cai_settings_dict = global_settings_dict.get(
            self._cai_settings_key, {})
        self._cai_settings = CAISettings(cai_settings_dict)

    def get_cai_settings(self):
        return self._cai_settings

    def get_dict(self) -> dict:
        return {
            self._cai_settings_key: self._cai_settings.get_dict(),
        }
