"""Test script to check banks data from 1C"""
from app.services.odata_1c_client import OData1CClient
from app.core.config import settings
import json

client = OData1CClient(
    base_url=settings.ODATA_1C_URL,
    username=settings.ODATA_1C_USERNAME,
    password=settings.ODATA_1C_PASSWORD
)

# Проверим справочник банков
try:
    banks = client._make_request("GET", "Catalog_КлассификаторБанков", {"$top": 5, "$format": "json"})
    print("=== Catalog_КлассификаторБанков ===")
    print(json.dumps(banks, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"КлассификаторБанков error: {e}")

print("\n")

# Проверим банковские счета
try:
    accounts = client._make_request("GET", "Catalog_БанковскиеСчетаОрганизаций", {"$top": 3, "$format": "json", "$expand": "Банк"})
    print("=== Catalog_БанковскиеСчетаОрганизаций ===")
    print(json.dumps(accounts, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"БанковскиеСчетаОрганизаций error: {e}")

print("\n")

# Проверим последнее поступление
try:
    receipt = client._make_request("GET", "Document_ПоступлениеНаРасчетныйСчет", {"$top": 1, "$format": "json"})
    print("=== Sample Receipt ===")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))
except Exception as e:
    print(f"Receipt error: {e}")
