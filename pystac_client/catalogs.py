from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Any, ClassVar, cast

import pystac

from pystac_client._utils import Modifiable, child_href, stac_body
from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import APIError
from pystac_client.mixins import BaseMixin

if TYPE_CHECKING:
    from pystac_client.catalog_client import CatalogClient
    from pystac_client.client import Client


class CatalogsMixin(BaseMixin):
    """Mixin for the experimental `Multi-Tenant Catalogs extension
    <https://github.com/StacLabs/multi-tenant-catalogs>`__.

    :class:`~pystac_client.Client` includes these methods. They read the
    ``/catalogs`` registry, return a :class:`~pystac_client.CatalogClient` for each
    catalog, and create, update, and disband catalogs. Each method checks the
    extension's conformance classes on the API root.

    Only :class:`~pystac_client.Client` and its subclasses can use this mixin.
    """

    catalog_client_class: ClassVar["type[CatalogClient] | None"] = None
    """The class of the clients returned by :meth:`get_catalog` and
    :meth:`get_catalogs`. ``None`` means :class:`~pystac_client.CatalogClient`."""

    modifier: Callable[[Modifiable], None] | None

    if TYPE_CHECKING:

        def _delete(self, url: str) -> None: ...

        def _validate_create_body(self, body: dict[str, Any], kind: str) -> None: ...

        def _write(
            self, url: str, method: str, body: dict[str, Any], stac_type: str
        ) -> dict[str, Any] | None: ...

    def get_catalogs(self) -> Iterator["CatalogClient"]:
        """Get the catalogs in this Catalog/API.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        On the API root, gets the catalogs registered at ``/catalogs``. On a
        :class:`~pystac_client.CatalogClient`, gets the sub-catalogs at
        ``/catalogs/{catalogId}/catalogs``. The API must support the
        ``MULTI_TENANT_CATALOGS`` conformance class.

        Return:
            Iterator[CatalogClient]: A client scoped to each catalog. See
            :meth:`get_catalog`.
        """
        self._api_root()._require_conforms_to(ConformanceClasses.MULTI_TENANT_CATALOGS)
        assert self._stac_io is not None
        for page in self._stac_io.get_pages(self._catalogs_href()):
            if "catalogs" not in page:
                raise APIError("Invalid response from /catalogs")
            for catalog in page["catalogs"]:
                yield self._catalog_from_dict(catalog)

    def get_catalog(self, catalog_id: str) -> "CatalogClient | None":
        """Get a single catalog from the API's catalog registry.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``GET /catalogs/{catalogId}``, also when called on a
        :class:`~pystac_client.CatalogClient` of another catalog. The API must
        support the ``MULTI_TENANT_CATALOGS`` conformance class.

        Args:
            catalog_id : The id of the catalog to get.

        Return:
            CatalogClient or None: A client scoped to the catalog, or None if it
            does not exist.
        """
        if not catalog_id:
            raise ValueError("A `catalog_id` must be provided.")
        api_root = self._api_root()
        api_root._require_conforms_to(ConformanceClasses.MULTI_TENANT_CATALOGS)
        data = api_root._read_json_or_none(api_root._catalogs_href(catalog_id))
        return None if data is None else self._catalog_from_dict(data)

    def create_catalog(
        self, catalog: pystac.Catalog | dict[str, Any]
    ) -> "CatalogClient | None":
        """Create a catalog on the server.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        On the API root, sends ``POST /catalogs`` to create a top-level catalog. On
        a :class:`~pystac_client.CatalogClient`, sends
        ``POST /catalogs/{catalogId}/catalogs`` to create a sub-catalog. The API
        must support the ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.

        Args:
            catalog : A :class:`pystac.Catalog` or catalog :class:`dict`.

        Return:
            CatalogClient or None: A client scoped to the catalog from the server,
            or None if the server returns no catalog body.

        Raises:
            ValueError: If this is a :class:`~pystac_client.CatalogClient` and
                ``catalog`` has only an ``id``, which the extension treats as a
                link. Use :meth:`~pystac_client.CatalogClient.link_catalog`.
        """
        url = self._transaction_catalogs_href()
        body = stac_body(catalog, "catalog")
        self._validate_create_body(body, "catalog")
        return self._write_catalog(url, "POST", body)

    def update_catalog(
        self, catalog: pystac.Catalog | dict[str, Any]
    ) -> "CatalogClient | None":
        """Replace the metadata of an existing catalog on the server.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``PUT /catalogs/{catalogId}``, using the id of ``catalog``. The
        catalog keeps its parent and child catalogs and collections. The API must
        support the ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.

        Args:
            catalog : A :class:`pystac.Catalog` or catalog :class:`dict` that
                replaces the existing catalog.

        Return:
            CatalogClient or None: A client scoped to the catalog from the server,
            or None if the server returns no catalog body.
        """
        body = stac_body(catalog, "catalog")
        url = self._api_root()._transaction_catalogs_href(body["id"])
        return self._write_catalog(url, "PUT", body)

    def delete_catalog(self, catalog_id: str) -> None:
        """Disband a catalog on the server.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``DELETE /catalogs/{catalogId}``. This deletes the catalog but none of
        its sub-catalogs, collections, or items; children left without a parent
        catalog are adopted by the API root. The API must support the
        ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.

        Args:
            catalog_id : The id of the catalog to disband.
        """
        self._delete(self._api_root()._transaction_catalogs_href(catalog_id))

    def _api_root(self) -> "Client":
        return cast("Client", self)

    def _catalogs_href(self, catalog_id: str | None = None) -> str:
        return child_href(self._catalogs_base_href(), catalog_id)

    def _catalogs_base_href(self) -> str:
        return self._get_href("catalogs", self.get_single_link("catalogs"), "catalogs")

    def _transaction_catalogs_href(self, catalog_id: str | None = None) -> str:
        self._api_root()._require_conforms_to(
            ConformanceClasses.MULTI_TENANT_CATALOGS_TRANSACTION
        )
        if catalog_id == "":
            raise ValueError("A `catalog_id` must be provided.")
        return self._catalogs_href(catalog_id)

    def _write_catalog(
        self, url: str, method: str, body: dict[str, Any]
    ) -> "CatalogClient | None":
        data = self._write(url, method, body, "Catalog")
        return self._catalog_from_dict(data) if data else None

    def _catalog_from_dict(self, data: dict[str, Any]) -> "CatalogClient":
        from pystac_client.catalog_client import CatalogClient

        root = self._api_root()
        catalog_client_class = root.catalog_client_class or CatalogClient
        has_self_link = any(link.get("rel") == "self" for link in data.get("links", []))
        catalog = catalog_client_class.from_dict(
            data,
            href=None if has_self_link else root._catalogs_href(data["id"]),
            root=root,
            preserve_dict=False,
            modifier=self.modifier,
        )
        catalog._stac_io = root._stac_io
        return cast(CatalogClient, catalog)
