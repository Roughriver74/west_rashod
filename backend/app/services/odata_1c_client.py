"""
1C OData Integration Service

Сервис для интеграции с 1С через стандартный интерфейс OData
"""

import logging
import base64
from typing import Optional, Dict, Any, List
from datetime import datetime, date
from pathlib import Path
import requests
from requests.auth import HTTPBasicAuth

logger = logging.getLogger(__name__)


class OData1CClient:
    """Client for 1C OData API integration"""

    def __init__(self, base_url: str, username: str = None, password: str = None,
                 custom_auth_token: str = None):
        """
        Initialize 1C OData client

        Args:
            base_url: Base URL for OData endpoint (e.g., http://10.10.100.77/trade/odata/standard.odata)
            username: Username for authentication (if not using custom_auth_token)
            password: Password for authentication (if not using custom_auth_token)
            custom_auth_token: Custom authorization token (e.g., "Basic base64string")
        """
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.custom_auth_token = custom_auth_token
        self.session = requests.Session()

        # Use custom auth token if provided, otherwise use username/password
        if custom_auth_token:
            self.session.headers.update({
                'Authorization': custom_auth_token,
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            logger.debug("Using custom authorization token")
        else:
            self.session.auth = HTTPBasicAuth(username, password)
            self.session.headers.update({
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            })
            logger.debug(f"Using HTTPBasicAuth with username: {username}")

    def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        timeout: int = 30
    ) -> Dict[str, Any]:
        """
        Make HTTP request to OData API

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (without base URL)
            params: Query parameters
            data: Request body data
            timeout: Request timeout in seconds

        Returns:
            Response data as dictionary

        Raises:
            requests.exceptions.RequestException: On request errors
        """
        # Для POST запросов используем http.client
        if method == 'POST' and data:
            import http.client
            import json as json_lib
            from urllib.parse import quote, urlparse

            parsed = urlparse(self.base_url)
            encoded_endpoint = quote(endpoint, safe='/:?=.$&_')
            full_endpoint = f"{parsed.path.rstrip('/')}/{encoded_endpoint.lstrip('/')}?$format=json"

            conn = http.client.HTTPConnection(parsed.netloc, timeout=timeout)

            try:
                payload = json_lib.dumps(data, ensure_ascii=False).encode('utf-8')

                if self.custom_auth_token:
                    auth_header = self.custom_auth_token
                elif self.username is not None and self.password is not None:
                    auth_string = f"{self.username}:{self.password}"
                    auth_b64 = base64.b64encode(auth_string.encode('utf-8')).decode('ascii')
                    auth_header = f"Basic {auth_b64}"
                else:
                    auth_header = self.session.headers.get('Authorization')
                    if not auth_header:
                        raise ValueError("Authorization is not configured for 1C OData POST request")

                conn.request(
                    method,
                    full_endpoint,
                    payload,
                    {
                        'Authorization': auth_header,
                        'Content-Type': 'application/json; charset=utf-8'
                    }
                )

                http_response = conn.getresponse()
                response_data = http_response.read()

                if http_response.status >= 400:
                    error_text = response_data.decode('utf-8')
                    logger.error(f"HTTP error: {http_response.status} {http_response.reason}")
                    logger.error(f"URL: {parsed.scheme}://{parsed.netloc}{full_endpoint}")
                    logger.error(f"Response: {error_text}")
                    raise requests.exceptions.HTTPError(
                        f"{http_response.status} {http_response.reason}",
                        response=type('obj', (object,), {
                            'status_code': http_response.status,
                            'text': error_text,
                            'content': response_data
                        })()
                    )

                if response_data:
                    return json_lib.loads(response_data.decode('utf-8'))
                return {}

            finally:
                conn.close()

        # Для GET и других запросов используем requests
        from urllib.parse import quote
        encoded_endpoint = quote(endpoint.lstrip('/'), safe='/:?=.$&_')
        url = f"{self.base_url}/{encoded_endpoint}"

        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=timeout
            )
            response.raise_for_status()

            if not response.content:
                return {}

            return response.json()

        except requests.exceptions.HTTPError as e:
            if e.response is not None:
                try:
                    error_json = e.response.json()
                    error_details = str(error_json)[:200]
                except:
                    error_details = e.response.text[:200] if e.response.text else "Empty response"
                logger.error(f"1C HTTP error {e.response.status_code}: {url} - {error_details}")
            else:
                logger.error(f"1C HTTP error: {url} - {str(e)[:200]}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"1C request error: {url} - {str(e)[:200]}")
            raise
        except ValueError as e:
            logger.error(f"1C JSON decode error: {url} - {str(e)[:200]}")
            raise

    def get_bank_receipts(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top: int = 100,
        skip: int = 0,
        only_posted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить поступления денежных средств из 1С

        Args:
            date_from: Начальная дата периода
            date_to: Конечная дата периода
            top: Количество записей (max 1000)
            skip: Пропустить N записей (для пагинации)
            only_posted: Deprecated (always True)

        Returns:
            Список документов поступлений
        """
        top_value = min(top, 1000)
        endpoint_with_params = f'Document_ПоступлениеБезналичныхДенежныхСредств?$top={top_value}&$format=json&$skip={skip}'
        mandatory_filters = "Posted eq true and DeletionMark eq false"

        if date_from and date_to:
            filter_str = f"{mandatory_filters} and Date ge datetime'{date_from.isoformat()}T00:00:00' and Date le datetime'{date_to.isoformat()}T23:59:59'"
            endpoint_with_params += f'&$filter={filter_str}'
        elif date_from:
            filter_str = f"{mandatory_filters} and Date ge datetime'{date_from.isoformat()}T00:00:00'"
            endpoint_with_params += f'&$filter={filter_str}'
        elif date_to:
            filter_str = f"{mandatory_filters} and Date le datetime'{date_to.isoformat()}T23:59:59'"
            endpoint_with_params += f'&$filter={filter_str}'
        else:
            endpoint_with_params += f'&$filter={mandatory_filters}'

        logger.debug(f"Fetching bank receipts: date_from={date_from}, date_to={date_to}, top={top}, skip={skip}")

        response = self._make_request(
            method='GET',
            endpoint=endpoint_with_params,
            params=None
        )

        results = response.get('value', [])

        if results:
            results = [
                r for r in results
                if r.get('Date') and r.get('Date') != '0001-01-01T00:00:00'
            ]

        return results

    def get_bank_payments(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top: int = 100,
        skip: int = 0,
        only_posted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить списания денежных средств из 1С

        Args:
            date_from: Начальная дата периода
            date_to: Конечная дата периода
            top: Количество записей (max 1000)
            skip: Пропустить N записей (для пагинации)
            only_posted: Deprecated (always True)

        Returns:
            Список документов списаний
        """
        top_value = min(top, 1000)
        endpoint_with_params = f'Document_СписаниеБезналичныхДенежныхСредств?$top={top_value}&$format=json&$skip={skip}'
        mandatory_filters = "Posted eq true and DeletionMark eq false"

        if date_from and date_to:
            filter_str = f"{mandatory_filters} and Date ge datetime'{date_from.isoformat()}T00:00:00' and Date le datetime'{date_to.isoformat()}T23:59:59'"
            endpoint_with_params += f'&$filter={filter_str}'
        elif date_from:
            filter_str = f"{mandatory_filters} and Date ge datetime'{date_from.isoformat()}T00:00:00'"
            endpoint_with_params += f'&$filter={filter_str}'
        elif date_to:
            filter_str = f"{mandatory_filters} and Date le datetime'{date_to.isoformat()}T23:59:59'"
            endpoint_with_params += f'&$filter={filter_str}'
        else:
            endpoint_with_params += f'&$filter={mandatory_filters}'

        logger.debug(f"Fetching bank payments: date_from={date_from}, date_to={date_to}, top={top}, skip={skip}")

        response = self._make_request(
            method='GET',
            endpoint=endpoint_with_params,
            params=None
        )

        results = response.get('value', [])

        if results:
            results = [
                r for r in results
                if r.get('Date') and r.get('Date') != '0001-01-01T00:00:00'
            ]

        return results

    def get_cash_receipts(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top: int = 100,
        skip: int = 0,
        only_posted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить приходные кассовые ордера (ПКО) из 1С
        """
        top_value = min(top, 1000)
        endpoint_with_params = f'Document_ПриходныйКассовыйОрдер?$top={top_value}&$format=json&$skip={skip}'
        mandatory_filters = "Posted eq true and DeletionMark eq false"

        if date_from and date_to:
            if date_from.year == date_to.year and date_from.month == date_to.month:
                filter_str = f'{mandatory_filters} and year(Date) eq {date_from.year} and month(Date) eq {date_from.month}'
                endpoint_with_params += f'&$filter={filter_str}'
            else:
                year_filter = date_from.year - 1
                filter_str = f'{mandatory_filters} and year(Date) gt {year_filter}'
                endpoint_with_params += f'&$filter={filter_str}'
        elif date_from:
            year_filter = date_from.year - 1
            filter_str = f'{mandatory_filters} and year(Date) gt {year_filter}'
            endpoint_with_params += f'&$filter={filter_str}'
        else:
            endpoint_with_params += f'&$filter={mandatory_filters}'

        logger.debug(f"Fetching cash receipts: date_from={date_from}, date_to={date_to}, top={top}, skip={skip}")

        response = self._make_request(
            method='GET',
            endpoint=endpoint_with_params,
            params=None
        )

        results = response.get('value', [])

        if results:
            results = [
                r for r in results
                if r.get('Date') and r.get('Date') != '0001-01-01T00:00:00'
            ]

        return results

    def get_cash_payments(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        top: int = 100,
        skip: int = 0,
        only_posted: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить расходные кассовые ордера (РКО) из 1С
        """
        top_value = min(top, 1000)
        endpoint_with_params = f'Document_РасходныйКассовыйОрдер?$top={top_value}&$format=json&$skip={skip}'
        mandatory_filters = "Posted eq true and DeletionMark eq false"

        if date_from and date_to:
            if date_from.year == date_to.year and date_from.month == date_to.month:
                filter_str = f'{mandatory_filters} and year(Date) eq {date_from.year} and month(Date) eq {date_from.month}'
                endpoint_with_params += f'&$filter={filter_str}'
            else:
                year_filter = date_from.year - 1
                filter_str = f'{mandatory_filters} and year(Date) gt {year_filter}'
                endpoint_with_params += f'&$filter={filter_str}'
        elif date_from:
            year_filter = date_from.year - 1
            filter_str = f'{mandatory_filters} and year(Date) gt {year_filter}'
            endpoint_with_params += f'&$filter={filter_str}'
        else:
            endpoint_with_params += f'&$filter={mandatory_filters}'

        logger.debug(f"Fetching cash payments: date_from={date_from}, date_to={date_to}, top={top}, skip={skip}")

        response = self._make_request(
            method='GET',
            endpoint=endpoint_with_params,
            params=None
        )

        results = response.get('value', [])

        if results:
            results = [
                r for r in results
                if r.get('Date') and r.get('Date') != '0001-01-01T00:00:00'
            ]

        return results

    def get_counterparty_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Получить контрагента по ключу

        Args:
            key: GUID контрагента

        Returns:
            Данные контрагента или None
        """
        if not key or key == "00000000-0000-0000-0000-000000000000":
            return None

        try:
            response = self._make_request(
                method='GET',
                endpoint=f"Catalog_Контрагенты(guid'{key}')",
                params={'$format': 'json'}
            )
            return response
        except Exception as e:
            logger.warning(f"Failed to fetch counterparty {key}: {e}")
            return None

    def get_organization_by_key(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Получить организацию по ключу

        Args:
            key: GUID организации

        Returns:
            Данные организации или None
        """
        if not key or key == "00000000-0000-0000-0000-000000000000":
            return None

        try:
            response = self._make_request(
                method='GET',
                endpoint=f"Catalog_Организации(guid'{key}')",
                params={'$format': 'json'}
            )
            return response
        except Exception as e:
            logger.warning(f"Failed to fetch organization {key}: {e}")
            return None

    def get_organizations(
        self,
        top: int = 100,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Получить список организаций из 1С
        """
        top_value = min(top, 1000)
        endpoint_with_params = f'Catalog_Организации?$top={top_value}&$format=json&$skip={skip}'

        logger.debug(f"Fetching organizations: top={top}, skip={skip}")

        response = self._make_request(
            method='GET',
            endpoint=endpoint_with_params,
            params=None
        )

        results = response.get('value', [])
        logger.debug(f"Fetched {len(results)} organizations")

        return results

    def get_cash_flow_categories(
        self,
        top: int = 1000,
        skip: int = 0,
        include_folders: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Получить статьи движения денежных средств из 1С

        Args:
            top: Количество записей (max 1000, default 1000)
            skip: Пропустить N записей (для пагинации)
            include_folders: Включать папки (группы) в результат

        Returns:
            Список статей ДДС
        """
        top_value = min(top, 1000)
        filter_str = "DeletionMark eq false"
        endpoint_with_params = f'Catalog_СтатьиДвиженияДенежныхСредств?$top={top_value}&$format=json&$skip={skip}&$filter={filter_str}'

        logger.debug(f"Fetching cash flow categories: top={top_value}, skip={skip}")

        response = self._make_request(
            method='GET',
            endpoint=endpoint_with_params,
            params=None
        )

        results = response.get('value', [])

        if not include_folders:
            results = [r for r in results if not r.get('IsFolder', False)]

        logger.debug(f"Fetched {len(results)} cash flow categories")

        return results

    def get_counterparty_by_inn(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Получить контрагента по ИНН
        """
        if not inn:
            return None

        try:
            filter_str = f"ИНН eq '{inn}'"
            endpoint_with_params = f"Catalog_Контрагенты?$top=1&$format=json&$filter={filter_str}"

            logger.debug(f"Searching counterparty by INN: {inn}")

            response = self._make_request(
                method='GET',
                endpoint=endpoint_with_params,
                params=None
            )

            results = response.get('value', [])
            if results:
                logger.debug(f"Found counterparty with INN {inn}: {results[0].get('Description')}")
                return results[0]
            else:
                logger.warning(f"Counterparty with INN {inn} not found in 1C")
                return None

        except Exception as e:
            logger.error(f"Failed to search counterparty by INN {inn}: {e}")
            return None

    def get_organization_by_inn(self, inn: str) -> Optional[Dict[str, Any]]:
        """
        Получить организацию по ИНН
        """
        if not inn:
            return None

        try:
            filter_str = f"ИНН eq '{inn}'"
            endpoint_with_params = f"Catalog_Организации?$top=1&$format=json&$filter={filter_str}"

            logger.debug(f"Searching organization by INN: {inn}")

            response = self._make_request(
                method='GET',
                endpoint=endpoint_with_params,
                params=None
            )

            results = response.get('value', [])
            if results:
                logger.debug(f"Found organization with INN {inn}: {results[0].get('Description')}")
                return results[0]
            else:
                logger.warning(f"Organization with INN {inn} not found in 1C")
                return None

        except Exception as e:
            logger.error(f"Failed to search organization by INN {inn}: {e}")
            return None

    def test_connection(self) -> bool:
        """
        Проверить подключение к 1С OData

        Returns:
            True если подключение успешно
        """
        try:
            response = self._make_request(
                method='GET',
                endpoint='',
                params={'$format': 'json'},
                timeout=10
            )
            logger.info("1C OData connection test successful")
            return True
        except Exception as e:
            logger.error(f"1C OData connection test failed: {e}")
            return False


_ODATA_ENV_LOADED = False


def _ensure_odata_env_loaded():
    """
    Ensure .env files are loaded so os.getenv picks up OData credentials.
    """
    global _ODATA_ENV_LOADED
    if _ODATA_ENV_LOADED:
        return

    try:
        from dotenv import load_dotenv
    except ImportError:
        _ODATA_ENV_LOADED = True
        return

    service_path = Path(__file__).resolve()
    backend_dir = service_path.parents[2]  # .../backend
    project_root = backend_dir.parent

    env_candidates = [
        project_root / ".env",
        backend_dir / ".env"
    ]

    for env_path in env_candidates:
        if env_path.is_file():
            load_dotenv(env_path, override=False)

    _ODATA_ENV_LOADED = True


def create_1c_client_from_env() -> OData1CClient:
    """
    Создать клиент 1С OData из переменных окружения

    Environment variables:
        ODATA_1C_URL: Base URL for OData
        ODATA_1C_USERNAME: Username (used if custom token is not set)
        ODATA_1C_PASSWORD: Password (used if custom token is not set)
        ODATA_1C_CUSTOM_AUTH_TOKEN: Optional full Authorization header value

    Returns:
        Configured OData1CClient instance
    """
    import os

    _ensure_odata_env_loaded()

    url = os.getenv('ODATA_1C_URL', 'http://10.10.100.77/trade/odata/standard.odata')
    username = os.getenv('ODATA_1C_USERNAME', 'odata.user')
    password = os.getenv('ODATA_1C_PASSWORD', 'ak228Hu2hbs28')
    custom_auth = os.getenv('ODATA_1C_CUSTOM_AUTH_TOKEN')

    client_kwargs: Dict[str, Any] = {'base_url': url}

    if custom_auth:
        client_kwargs['custom_auth_token'] = custom_auth.strip()
    else:
        client_kwargs['username'] = username
        client_kwargs['password'] = password

    return OData1CClient(**client_kwargs)
