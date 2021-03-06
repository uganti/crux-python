"""Module contains code pertaining to CruxClient."""

from typing import (  # noqa: F401 pylint: disable=unused-import
    Any,
    Dict,
    List,
    MutableMapping,
    Optional,
    Text,
    Tuple,
    Union,
)

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import (
    ConnectTimeout,
    HTTPError,
    ProxyError,
    ReadTimeout,
    SSLError,
    TooManyRedirects,
)
from requests.packages.urllib3.util.retry import (  # Dynamic load pylint: disable=import-error
    Retry,
)

from crux.config import CruxConfig
from crux.exceptions import (
    CruxAPIError,
    CruxClientConnectionError,
    CruxClientHTTPError,
    CruxClientTimeout,
    CruxResourceNotFoundError,
)
from crux.utils import url_builder


class CruxClient(object):
    """Crux HTTP REST client."""

    def __init__(self, crux_config):
        # type: (CruxConfig) -> None
        if crux_config is None:
            self.crux_config = CruxConfig()  # type: CruxConfig
        else:
            self.crux_config = crux_config  # type: CruxConfig

    def api_call(  # pylint: disable=too-many-branches,too-many-statements
        self,
        method,  # type: str
        path,  # type: List[str]
        model=None,  # type: Any
        headers=None,  # type: MutableMapping[Text, Text]
        params=None,  # type: Dict[Any,Any]
        data=None,  # type: Dict[Any,Any]
        stream=False,  # type: bool
        retries=20,  # type: int
        backoff=0.3,  # type: float
        status_forcelist=(
            500,
            502,
            503,
            504,
            520,
            521,
            522,
            523,
            524,
            525,
            527,
            530,
        ),  # type: Tuple
        retry_on_methods=("GET", "PUT", "DELETE", "POST"),  # type: Tuple
        max_http_redirects=10,  # type: int
        timeout=60,  # type: int
        max_conn_errors=10,  # type: int
    ):
        # type:(...) -> Any
        """
        Requests and Serializes response from API Backend.

        Args:
            method (str): REST method name.
            path (str): API resource path.
            model (crux.models.CruxModel): Deserialization Model. Defaults to None.
            headers (dict): Additonal header parameters. Defaults to None.
            params (dict): Body data to be passed with request. Defaults to None.
            data (dict): Should be used while passing form encoded data. Defaults to None.
            stream (bool): Should be set to True, when response is required to be streamed.
                Defaults to False.
            retries (int): Total Retries to be performed. Defaults to 20.
            backoff (float): Backoff factor to be applied. Defaults to 0.3.
                {backoff factor} * (2 ^ ({number of total retries} - 1))
            status_forcelist (tuple): A set of integer HTTP status codes
                that should be retried on.
                Defaults to (500, 502, 503, 504, 520, 521, 522, 523, 524, 525, 527, 530).
            retry_on_methods (tuple): A set of uppercased HTTP method verbs
                that we should retry on.
                Defaults to ("GET", "PUT", "DELETE", "POST").
            max_http_redirects (int): Max HTTP sredirects to perform on API calls.
                Defaults to 10.
            timeout (int): Request timeout configuration in seconds.
                Defaults to 60.
            max_conn_errors (int): Max connection-related errors to retry on.
                Defaults to 10.

        Returns:
            crux.models.Model or bool: Serialized response from API backend.

        Raises:
            TypeError: If Path is not of list type.
            CruxClientHTTPError: If there is HTTP related error.
            CruxClientConnectionError: If there is SSL or Proxy related error.
            CruxClientTimeout: If there is timout related error.
            CruxResourceNotFoundError: If API has status code 400.
            CruxAPIError: If API has status code other than 2XX.
        """

        if path is None or not isinstance(path, list):
            raise TypeError("Path cannot be of NoneType. It should be of Type List")

        url = url_builder(
            url_base=self.crux_config.api_host,
            url_prefix=self.crux_config.api_prefix,
            url_path_list=path,
        )

        if headers is None:
            headers = {}

        if params is None:
            params = {}

        auth_scheme = "Bearer"  # type: str
        bearer_token = "{scheme} {key}".format(
            scheme=auth_scheme, key=self.crux_config.api_key
        )  # type: Text

        user_agent = self.crux_config.user_agent  # type: Text

        headers.update({"Authorization": bearer_token, "User-Agent": user_agent})

        retry = Retry(
            total=retries,
            backoff_factor=backoff,
            status_forcelist=status_forcelist,
            method_whitelist=retry_on_methods,
            redirect=max_http_redirects,
            connect=max_conn_errors,
        )

        adapter = HTTPAdapter(max_retries=retry)

        if method in ("GET", "DELETE"):
            try:
                with requests.session() as session:
                    session.mount("http://", adapter)
                    session.mount("https://", adapter)
                    response = session.request(
                        method,
                        url,
                        headers=headers,
                        params=params,
                        stream=stream,
                        proxies=self.crux_config.proxies,
                        timeout=timeout,
                    )
            except (HTTPError, TooManyRedirects) as err:
                raise CruxClientHTTPError(str(err))
            except (ProxyError, SSLError) as err:
                raise CruxClientConnectionError(str(err))
            except (ConnectTimeout, ReadTimeout) as err:
                raise CruxClientTimeout(str(err))
        elif method in ("PUT", "POST"):
            try:
                if data:
                    with requests.session() as session:
                        session.mount("http://", adapter)
                        session.mount("https://", adapter)
                        response = session.request(
                            method,
                            url,
                            headers=headers,
                            data=data,
                            proxies=self.crux_config.proxies,
                            timeout=timeout,
                        )
                else:
                    with requests.session() as session:
                        session.mount("http://", adapter)
                        session.mount("https://", adapter)
                        response = session.request(
                            method,
                            url,
                            headers=headers,
                            json=params,
                            proxies=self.crux_config.proxies,
                            timeout=timeout,
                        )
            except (HTTPError, TooManyRedirects) as err:
                raise CruxClientHTTPError(str(err))
            except (ProxyError, SSLError) as err:
                raise CruxClientConnectionError(str(err))
            except (ConnectTimeout, ReadTimeout) as err:
                raise CruxClientTimeout(str(err))
        else:
            raise ValueError("Request Method Type should be in GET, DELETE, PUT, POST")

        if response.status_code in (200, 201, 202, 206):
            if model is None:
                return response
            else:
                if isinstance(response.json(), list):
                    serial_list = []
                    for item in response.json():
                        obj = model.from_dict(item)
                        obj.connection = self
                        obj.raw_response = response.json()
                        serial_list.append(obj)
                    return serial_list
                else:
                    obj = model.from_dict(response.json())
                    obj.connection = self
                    obj.raw_response = response.json()
                    return obj
        elif response.status_code == 204:
            return True
        else:
            if response.status_code == 404:
                raise CruxResourceNotFoundError(response.json())
            else:
                raise CruxAPIError(response.json())
