from __future__ import annotations

import warnings
from collections.abc import Callable, Iterator
from typing import (
    TYPE_CHECKING,
    Any,
    Optional,
    cast,
)

import pystac
from pystac.layout import APILayoutStrategy, HrefLayoutStrategy

from pystac_client._utils import Modifiable, call_modifier
from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import APIError
from pystac_client.item_search import ItemSearch
from pystac_client.mixins import QueryablesMixin
from pystac_client.stac_api_io import StacApiIO
from pystac_client.warnings import FallbackToPystac

if TYPE_CHECKING:
    from pystac.item import Item as Item_Type

    from pystac_client import Client


class CollectionClient(pystac.Collection, QueryablesMixin):
    modifier: Callable[[Modifiable], None]
    _stac_io: StacApiIO
    _fallback_strategy: HrefLayoutStrategy = APILayoutStrategy()

    def __init__(
        self,
        id: str,
        description: str,
        extent: pystac.Extent,
        title: str | None = None,
        stac_extensions: list[str] | None = None,
        href: str | None = None,
        extra_fields: dict[str, Any] | None = None,
        catalog_type: pystac.CatalogType | None = None,
        license: str = "proprietary",
        keywords: list[str] | None = None,
        providers: list[pystac.Provider] | None = None,
        summaries: pystac.Summaries | None = None,
        assets: dict[str, pystac.Asset] | None = None,
        strategy: HrefLayoutStrategy | None = None,
        *,
        modifier: Callable[[Modifiable], None] | None = None,
        **kwargs: dict[str, Any],
    ):
        super().__init__(
            id,
            description,
            extent,
            title,
            stac_extensions,
            href,
            extra_fields,
            catalog_type,
            license,
            keywords,
            providers,
            summaries,
            assets,
            strategy,
            **kwargs,
        )
        # error: Cannot assign to a method  [assignment]
        # https://github.com/python/mypy/issues/2427
        setattr(self, "modifier", modifier)

    @classmethod
    def from_dict(
        cls,
        d: dict[str, Any],
        href: str | None = None,
        root: pystac.Catalog | Client | None = None,
        migrate: bool = False,
        preserve_dict: bool = True,
        modifier: Callable[[Modifiable], None] | None = None,
    ) -> CollectionClient:
        result = super().from_dict(d, href, root, migrate, preserve_dict)
        # error: Cannot assign to a method  [assignment]
        # https://github.com/python/mypy/issues/2427
        setattr(result, "modifier", modifier)
        return result

    def __repr__(self) -> str:
        return f"<CollectionClient id={self.id}>"

    def set_root(self, root: pystac.Catalog | Client | None) -> None:
        # hook in to set_root and use it for setting _stac_io
        super().set_root(root=root)
        if root is None:
            raise ValueError("`CollectionClient.root` must be set")
        elif root._stac_io is not None and isinstance(root._stac_io, StacApiIO):
            self._stac_io = root._stac_io
        else:
            raise ValueError("`CollectionClient.root` must be a valid `Client` object")

    def get_root(self) -> Client:
        from pystac_client.client import Client

        root = super().get_root()
        if root is None or not isinstance(root, Client):
            raise ValueError(
                "`CollectionClient.root` is not have a valid `Client` object."
            )
        return root

    def conforms_to(self, conformance_class: ConformanceClasses | str) -> bool:
        root = self.get_root()
        return root.conforms_to(conformance_class)

    def get_items(self, *ids: str, recursive: bool = False) -> Iterator[Item_Type]:
        """Return all items in this Collection or specific items.

        If the Collection contains a link of with a `rel` value of `items`,
        that link will be used to iterate through items. Otherwise, the default
        PySTAC behavior is assumed.

        Args:
            ids: Items ids to retrieve
            recursive: If True, search every child collection as well as this one.

        Return:
            Iterator[Item]: Iterator of items whose parent is this catalog.
        """
        if recursive is True:
            yield from super().get_items(*ids, recursive=True)
        else:
            root = self.get_root()
            if root.conforms_to(ConformanceClasses.ITEM_SEARCH):
                url = root._search_href() if ids else self._items_href()

                search = ItemSearch(
                    url=url,
                    method="GET",
                    client=root,
                    ids=ids,
                    collections=[self.id],
                    modifier=self.modifier,
                )
                yield from search.items()
            else:
                root._warn_about_fallback("ITEM_SEARCH")
                for item in super().get_items(*ids):
                    call_modifier(self.modifier, item)
                    yield item

    def get_item(self, id: str, recursive: bool = False) -> Item_Type | None:
        """Returns an item with a given ID.

        If the collection conforms to
        [ogcapi-features](https://github.com/radiantearth/stac-api-spec/blob/738f4837ac6bea041dc226219e6d13b2c577fb19/ogcapi-features/README.md),
        this will use the `/collections/{collectionId}/items/{featureId}`.
        If not, and the collection conforms to [item
        search](https://github.com/radiantearth/stac-api-spec/blob/2d3c0cf644af9976eecbf32aec77b9a137268e12/item-search/README.md),
        this will use `/search?ids={featureId}&collections={collectionId}`.
        Otherwise, the default PySTAC behavior is used.

        Args:
            id : The ID of the item to find.
            recursive : If True, search this catalog and all children for the
                item; otherwise, only search the items of this catalog. Defaults
                to False.

        Return:
            Item or None: The item with the given ID, or None if not found.
        """
        if not recursive:
            root = self.get_root()
            if root.conforms_to(ConformanceClasses.FEATURES) and self._stac_io:
                url = f"{self._items_href().rstrip('/')}/{id}"
                try:
                    obj = self._stac_io.read_stac_object(url, root=self)
                    item = cast(Optional[pystac.Item], obj)
                except APIError as err:
                    if getattr(err, "status_code", None) and err.status_code == 404:
                        return None
                    else:
                        raise err
            elif root.conforms_to(ConformanceClasses.ITEM_SEARCH) and self._stac_io:
                item_search = ItemSearch(
                    url=root._search_href(),
                    method="GET",
                    client=root,
                    ids=[id],
                    collections=[self.id],
                    modifier=self.modifier,
                )
                item = next(item_search.items(), None)
            else:
                root._warn_about_fallback("FEATURES", "ITEM_SEARCH")
                item = super().get_item(id, recursive=False)
        else:
            warnings.warn(FallbackToPystac())
            item = super().get_item(id, recursive=True)

        if item:
            call_modifier(self.modifier, item)

        return item

    def _items_href(self) -> str:
        link = self.get_single_link("items")
        href = self._get_href("items", link, "items")
        return href
