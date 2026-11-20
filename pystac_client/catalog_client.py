from typing import Any

from pystac_client._utils import urljoin
from pystac_client.client import Client
from pystac_client.collection_client import CollectionClient
from pystac_client.conformance import ConformanceClasses


class CatalogClient(Client):
    """A :class:`~pystac_client.Client` scoped to a catalog of the experimental
    `Multi-Tenant Catalogs extension
    <https://github.com/StacLabs/multi-tenant-catalogs>`__.

    .. warning::

        Experimental: this class follows the `Multi-Tenant Catalogs extension
        <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
        Proposal maturity, and may change with it.

    :meth:`~pystac_client.catalogs.CatalogsMixin.get_catalog` and
    :meth:`~pystac_client.catalogs.CatalogsMixin.get_catalogs` return instances of
    this class; it cannot be opened with :meth:`~pystac_client.Client.open`. They
    use the endpoints of the catalog:

    * :meth:`~pystac_client.Client.get_collections` and
      :meth:`~pystac_client.Client.get_collection` read
      ``/catalogs/{catalogId}/collections``.
    * :meth:`~pystac_client.catalogs.CatalogsMixin.get_catalogs` reads, and
      :meth:`~pystac_client.catalogs.CatalogsMixin.create_catalog` writes,
      ``/catalogs/{catalogId}/catalogs``.
    * :meth:`~pystac_client.Client.search` searches every collection below the
      catalog at ``/catalogs/{catalogId}/search``. The API must also support the
      ``MULTI_TENANT_CATALOGS_SEARCH`` conformance class.
    * :meth:`~pystac_client.Client.create_collection` and
      :meth:`~pystac_client.Client.update_collection` write
      ``/catalogs/{catalogId}/collections``. The API must support the
      ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.
    * :meth:`patch_collection`, :meth:`delete_collection`, and item writes on its
      collections use ``/collections/{collectionId}`` of the API root.

    ``create_catalog`` and ``create_collection`` raise a :exc:`ValueError` for a
    body with only an ``id``, which the extension treats as a link. Use
    :meth:`link_catalog` or :meth:`link_collection` instead.

    Its conformance classes are the ``conformsTo`` of the catalog, or the current
    ones of the API root if the catalog has none. The Multi-Tenant Catalogs,
    Transaction, and Collection Transaction conformance classes are always checked
    on the API root.
    """

    def __repr__(self) -> str:
        return f"<CatalogClient id={self.id}>"

    @classmethod
    def from_file(cls, *args: Any, **kwargs: Any) -> Client:  # type: ignore
        """Not supported.

        Raises:
            TypeError: Always. Open the API root with
                :meth:`~pystac_client.Client.open` and use
                :meth:`~pystac_client.catalogs.CatalogsMixin.get_catalog`.
        """
        raise TypeError(
            "A CatalogClient cannot be opened directly. Open the API root with "
            "`Client.open` and use `get_catalog` or `get_catalogs`."
        )

    def has_conforms_to(self) -> bool:
        """Whether the catalog or the API root has a ``"conformsTo"`` list"""
        return super().has_conforms_to() or self._api_root().has_conforms_to()

    def get_conforms_to(self) -> list[str]:
        """List of ``"conformsTo"`` URIs of the catalog, or of the API root if the
        catalog has none

        Return:
            List[str]: List of URIs that the catalog conforms to
        """
        if super().has_conforms_to():
            return super().get_conforms_to()
        return self._api_root().get_conforms_to()

    def link_catalog(self, catalog_id: str) -> "CatalogClient | None":
        """Add an existing catalog as a sub-catalog of this catalog.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``POST /catalogs/{catalogId}/catalogs`` with only the catalog ``id``.
        The linked catalog keeps its other parent catalogs. The API must support
        the ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.

        Args:
            catalog_id : The id of an existing catalog.

        Return:
            CatalogClient or None: A client scoped to the linked catalog, or None if
            the server returns no catalog body.
        """
        url = self._transaction_catalogs_href()
        if not catalog_id:
            raise ValueError("A `catalog_id` must be provided.")
        return self._write_catalog(url, "POST", {"id": catalog_id})

    def unlink_catalog(self, catalog_id: str) -> None:
        """Remove a sub-catalog from this catalog without deleting it.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``DELETE /catalogs/{catalogId}/catalogs/{subCatalogId}``. A catalog
        left without a parent catalog is adopted by the API root. The API must
        support the ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.

        Args:
            catalog_id : The id of the sub-catalog to unlink.
        """
        self._delete(self._transaction_catalogs_href(catalog_id))

    def patch_collection(
        self, collection_id: str, patch: dict[str, Any]
    ) -> CollectionClient | None:
        """Partially update an existing collection on the server.

        Sends ``PATCH /collections/{collectionId}`` to the API root, see
        :meth:`pystac_client.Client.patch_collection`.

        Args:
            collection_id : The id of the collection to update.
            patch : The fields to change. Fields set to ``None`` are removed.

        Return:
            CollectionClient or None: The updated collection from the server, or None
            if the server returns no collection body, e.g. a ``202 Accepted`` for a
            queued operation.
        """
        return self._api_root().patch_collection(collection_id, patch)

    def delete_collection(self, collection_id: str) -> None:
        """Delete a collection on the server from every catalog.

        Sends ``DELETE /collections/{collectionId}`` to the API root, see
        :meth:`pystac_client.Client.delete_collection`. To only remove the
        collection from this catalog, use :meth:`unlink_collection`.

        Args:
            collection_id : The id of the collection to delete.
        """
        self._api_root().delete_collection(collection_id)

    def link_collection(self, collection_id: str) -> CollectionClient | None:
        """Add an existing collection to this catalog.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``POST /catalogs/{catalogId}/collections`` with only the collection
        ``id``. The collection keeps its other parent catalogs. The API must
        support the ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance class.

        Args:
            collection_id : The id of an existing collection.

        Return:
            CollectionClient or None: The linked collection from the server, or None
            if the server returns no collection body.
        """
        url = self._transaction_collections_href()
        if not collection_id:
            raise ValueError("A `collection_id` must be provided.")
        return self._write_collection(url, "POST", {"id": collection_id})

    def unlink_collection(self, collection_id: str) -> None:
        """Remove a collection from this catalog without deleting it.

        .. warning::

            Experimental: this method follows the `Multi-Tenant Catalogs extension
            <https://github.com/StacLabs/multi-tenant-catalogs>`__, which is at
            Proposal maturity, and may change with it.

        Sends ``DELETE /catalogs/{catalogId}/collections/{collectionId}``. A
        collection left without a parent catalog is adopted by the API root. The
        API must support the ``MULTI_TENANT_CATALOGS_TRANSACTION`` conformance
        class.

        Args:
            collection_id : The id of the collection to unlink.
        """
        self._delete(self._transaction_collections_href(collection_id))

    def _api_root(self) -> Client:
        root = self.get_root()
        if root is self or not isinstance(root, Client):
            raise ValueError(
                "A CatalogClient needs the API root as its root. Get one with "
                "`get_catalog` or `get_catalogs`."
            )
        return root

    def _catalogs_base_href(self) -> str:
        return urljoin(self.self_href, "catalogs")

    def _missing_item_search_conformance(self) -> ConformanceClasses | None:
        missing = super()._missing_item_search_conformance()
        if missing is None and not self._api_root().conforms_to(
            ConformanceClasses.MULTI_TENANT_CATALOGS_SEARCH
        ):
            return ConformanceClasses.MULTI_TENANT_CATALOGS_SEARCH
        return missing

    def _items_search_href(self) -> str:
        if self._supports_item_search():
            return self._search_href()
        return self._api_root()._search_href()

    def _require_collection_transaction(self) -> None:
        self._api_root()._require_conforms_to(
            ConformanceClasses.MULTI_TENANT_CATALOGS_TRANSACTION
        )

    def _transaction_items_href(self, collection: CollectionClient) -> str:
        api_root = self._api_root()
        api_root._require_conforms_to(ConformanceClasses.TRANSACTION)
        return urljoin(api_root._collections_href(collection.id), "items")

    def _validate_create_body(self, body: dict[str, Any], kind: str) -> None:
        if body.keys() == {"id"}:
            raise ValueError(
                "A body with only an `id` links an existing resource instead of "
                f"creating one. Use `link_{kind}` to link it."
            )
