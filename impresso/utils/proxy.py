import json
import logging
import socket
from typing import TypedDict
import sockslib

from impresso.base import get_env_variable

logger = logging.getLogger(__name__)


class ImpressoProxySettings(TypedDict):
    host: str
    port: int
    domains: list[str]


def proxy_interceptor(proxy_settings: ImpressoProxySettings | None = None):
    """
    Interceptor for MySQL connections to use a SOCKS proxy.
    """

    def decorator(original_connect):
        def wrapper(*args, **kwargs):
            host, port = kwargs["host"], kwargs["port"]

            if proxy_settings is not None and host in proxy_settings["domains"]:

                # Call the original connect method
                # with defer_connect=True to avoid immediate connection
                # and connect through the proxy later
                connection = original_connect(
                    *args, **{**kwargs, "defer_connect": True}
                )

                sockslib.set_default_proxy(
                    (proxy_settings["host"], proxy_settings["port"]),
                    sockslib.Socks.SOCKS5,
                    socket.AF_INET6,
                )

                s = sockslib.SocksSocket()
                s.connect((host, port))

                connection.connect(sock=s)

                logger.info(
                    "MySQL connection to %s established through SOCKS proxy (%s:%d).",
                    host,
                    proxy_settings["host"],
                    proxy_settings["port"],
                )
                return connection
            else:
                # If no proxy settings are provided or the host is not
                # in the domains,
                # call the original connect method without proxying
                return original_connect(*args, **kwargs)

        return wrapper

    return decorator


def load_proxy_settings() -> ImpressoProxySettings | None:
    """
    Load proxy settings from environment variables or return None if not set.
    """
    try:
        data = json.loads(get_env_variable("IMPRESSO_SOCKS_PROXY_CONFIG", None))

        return ImpressoProxySettings(**data)  # type: ignore[typeddict-item]
    except (KeyError, json.JSONDecodeError, TypeError):
        return None


def with_optional_proxy(original_connect):
    """
    Decorator to apply the proxy interceptor if proxy settings are provided.
    """
    proxy_settings = load_proxy_settings()

    if proxy_settings:
        return proxy_interceptor(proxy_settings)(original_connect)
    else:
        return original_connect
