"""
交易平台錯誤類型
"""


class BrokerError(Exception):
    """交易平台通用錯誤。"""


class BrokerConfigurationError(BrokerError):
    """交易平台設定錯誤。"""


class BrokerConnectionError(BrokerError):
    """交易平台連線錯誤。"""


class BrokerOrderRejected(BrokerError):
    """交易平台拒絕訂單。"""
