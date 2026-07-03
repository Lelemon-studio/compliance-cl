from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Any


def _items(response: Any) -> list[Any]:
    data = getattr(response, "data", response)
    items = getattr(data, "items", data)
    if items is None:
        return []
    if isinstance(items, list):
        return items
    if isinstance(items, tuple):
        return list(items)
    if isinstance(items, Iterable) and not isinstance(items, (str, bytes, dict)):
        return list(items)
    return [items]


def paginate(call: Callable[..., Any], *, max_retries: int = 4, **kwargs: Any) -> list[Any]:
    collected: list[Any] = []
    page: str | None = None
    retries = 0
    while True:
        try:
            response = call(page=page, **kwargs)
            retries = 0
        except Exception as exc:
            status = getattr(exc, "status", None)
            if status != 429 or retries >= max_retries:
                raise
            time.sleep(min(2**retries, 8))
            retries += 1
            continue
        collected.extend(_items(response))
        headers = getattr(response, "headers", {}) or {}
        page = headers.get("opc-next-page") or headers.get("opc_next_page")
        if not page:
            break
    return collected


def resolve_compartments(identity_client: Any, tenancy_ocid: str, requested: str | tuple[str, ...]) -> list[str]:
    if requested != "all":
        return list(requested)
    compartments = paginate(
        identity_client.list_compartments,
        compartment_id=tenancy_ocid,
        compartment_id_in_subtree=True,
        access_level="ACCESSIBLE",
    )
    identifiers = [tenancy_ocid]
    for item in compartments:
        identifier = item.get("id") if isinstance(item, dict) else getattr(item, "id", None)
        if identifier:
            identifiers.append(str(identifier))
    return list(dict.fromkeys(identifiers))


def resolve_availability_domains(identity_client: Any, compartment_id: str) -> list[str]:
    domains = paginate(identity_client.list_availability_domains, compartment_id=compartment_id)
    names: list[str] = []
    for domain in domains:
        name = domain.get("name") if isinstance(domain, dict) else getattr(domain, "name", None)
        if name:
            names.append(str(name))
    return list(dict.fromkeys(names))
