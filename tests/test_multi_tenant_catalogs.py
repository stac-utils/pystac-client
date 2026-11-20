import contextlib
from collections.abc import Callable
from typing import Any

import pystac
import pytest
from requests_mock import ANY, Mocker

from pystac_client import CatalogClient, Client, CollectionClient
from pystac_client._utils import Modifiable
from pystac_client.catalogs import CatalogsMixin
from pystac_client.exceptions import APIError
from pystac_client.warnings import DoesNotConformTo, MissingLink, PystacClientWarning

ROOT_URL = "https://stac.example.com"
REGISTRY_URL = f"{ROOT_URL}/catalogs"
CATALOG_URL = f"{REGISTRY_URL}/forestry"
SUB_CATALOGS_URL = f"{CATALOG_URL}/catalogs"
SCOPED_COLLECTIONS_URL = f"{CATALOG_URL}/collections"
COLLECTIONS_URL = f"{ROOT_URL}/collections"

MTC = "/multi-tenant-catalogs"
MTC_TRANSACTION = "/multi-tenant-catalogs/transaction"
MTC_SEARCH = "/multi-tenant-catalogs/search"
COLLECTION_TRANSACTION = "/collections/extensions/transaction"
ALL_CLASSES = (MTC, MTC_TRANSACTION, MTC_SEARCH, COLLECTION_TRANSACTION)


def _uri(path: str) -> str:
    return f"https://api.stacspec.org/v1.0.0{path}"


def _link(rel: str, href: str, **fields: Any) -> dict[str, Any]:
    return {"rel": rel, "href": href, "type": "application/json", **fields}


def _search_link(href: str) -> dict[str, Any]:
    return _link("search", href, type="application/geo+json", method="POST")


def root_dict(classes: tuple[str, ...], catalogs_link: bool = True) -> dict[str, Any]:
    links = [
        _link("self", ROOT_URL),
        _link("root", ROOT_URL),
        _link("data", COLLECTIONS_URL),
        _search_link(f"{ROOT_URL}/search"),
    ]
    if catalogs_link:
        links.append(_link("catalogs", REGISTRY_URL))
    conformance = ["/core", "/collections", "/ogcapi-features", "/item-search"]
    return {
        "type": "Catalog",
        "id": "root",
        "description": "An API with multi-tenant catalogs",
        "stac_version": "1.0.0",
        "conformsTo": [_uri(path) for path in [*conformance, *classes]],
        "links": links,
    }


def catalog_dict(catalog_id: str) -> dict[str, Any]:
    href = f"{REGISTRY_URL}/{catalog_id}"
    return {
        "type": "Catalog",
        "id": catalog_id,
        "description": f"The {catalog_id} catalog",
        "stac_version": "1.0.0",
        "links": [
            _link("self", href),
            _link("root", f"{ROOT_URL}/"),
            _link("parent", f"{ROOT_URL}/"),
            _link("data", f"{href}/collections"),
            _search_link(f"{href}/search"),
        ],
    }


def collection_dict(collection_id: str, collections_url: str) -> dict[str, Any]:
    href = f"{collections_url}/{collection_id}"
    return {
        "type": "Collection",
        "id": collection_id,
        "description": f"The {collection_id} collection",
        "license": "proprietary",
        "stac_version": "1.0.0",
        "extent": {
            "spatial": {"bbox": [[-180, -90, 180, 90]]},
            "temporal": {"interval": [[None, None]]},
        },
        "links": [_link("self", href), _link("items", f"{href}/items")],
    }


def _open_client(
    requests_mock: Mocker,
    classes: tuple[str, ...] = ALL_CLASSES,
    catalogs_link: bool = True,
    **client_kwargs: Any,
) -> Client:
    requests_mock.get(ROOT_URL, json=root_dict(classes, catalogs_link))
    return Client.open(ROOT_URL, **client_kwargs)


def _scoped_client(
    requests_mock: Mocker,
    classes: tuple[str, ...] = ALL_CLASSES,
    catalog_classes: tuple[str, ...] | None = None,
    **kwargs: Any,
) -> CatalogClient:
    client = _open_client(requests_mock, classes, **kwargs)
    data = catalog_dict("forestry")
    if catalog_classes is not None:
        data["conformsTo"] = [_uri(path) for path in catalog_classes]
    requests_mock.get(CATALOG_URL, json=data)
    catalog = client.get_catalog("forestry")
    assert catalog is not None
    return catalog


def test_client_includes_catalogs_mixin() -> None:
    assert issubclass(Client, CatalogsMixin)


@pytest.mark.parametrize(
    "method", ["link_catalog", "unlink_catalog", "link_collection", "unlink_collection"]
)
def test_link_methods_only_on_catalog_client(method: str) -> None:
    assert not hasattr(Client, method)
    assert hasattr(CatalogClient, method)


class CustomClient(Client):
    pass


class CustomCatalogClient(CatalogClient, CustomClient):
    pass


CustomClient.catalog_client_class = CustomCatalogClient


class TestCatalogClientClass:
    def test_get_catalog_returns_catalog_client(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)

        assert type(catalog) is CatalogClient
        assert repr(catalog) == "<CatalogClient id=forestry>"

    def test_custom_catalog_client_class(self, requests_mock: Mocker) -> None:
        requests_mock.get(ROOT_URL, json=root_dict(ALL_CLASSES))
        requests_mock.get(CATALOG_URL, json=catalog_dict("forestry"))
        requests_mock.get(
            SUB_CATALOGS_URL, json={"catalogs": [catalog_dict("fire")], "links": []}
        )
        client = CustomClient.open(ROOT_URL)

        catalog = client.get_catalog("forestry")
        assert catalog is not None
        sub_catalogs = list(catalog.get_catalogs())

        assert isinstance(catalog, CustomCatalogClient)
        assert all(isinstance(sub, CustomCatalogClient) for sub in sub_catalogs)

    def test_open_is_not_supported(self) -> None:
        with pytest.raises(TypeError, match="Open the API root with `Client.open`"):
            CatalogClient.open(CATALOG_URL)

    def test_needs_api_root(self) -> None:
        catalog = CatalogClient("forestry", "The forestry catalog")

        with pytest.raises(ValueError, match="needs the API root as its root"):
            catalog.get_conforms_to()

    def test_uses_current_api_root_conforms_to(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        root = catalog.get_root()
        assert isinstance(root, Client)

        root.remove_conforms_to("MULTI_TENANT_CATALOGS_SEARCH")

        assert catalog.has_conforms_to()
        assert catalog.get_conforms_to() == root.get_conforms_to()
        assert "conformsTo" not in catalog.extra_fields
        with pytest.raises(DoesNotConformTo, match="MULTI_TENANT_CATALOGS_SEARCH"):
            catalog.search()

    def test_own_conforms_to_ignores_api_root(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock, catalog_classes=("/core",))
        root = catalog.get_root()
        assert isinstance(root, Client)

        root.clear_conforms_to()

        assert catalog.get_conforms_to() == [_uri("/core")]


class TestReadCatalogs:
    def test_get_catalogs(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        next_url = f"{REGISTRY_URL}?token=2"
        requests_mock.get(
            REGISTRY_URL,
            [
                {
                    "json": {
                        "catalogs": [catalog_dict("forestry")],
                        "links": [_link("next", next_url)],
                    }
                },
            ],
        )
        requests_mock.get(
            next_url, json={"catalogs": [catalog_dict("fire")], "links": []}
        )

        catalogs = list(client.get_catalogs())

        assert [catalog.id for catalog in catalogs] == ["forestry", "fire"]
        assert all(isinstance(catalog, CatalogClient) for catalog in catalogs)
        assert catalogs[0].get_self_href() == CATALOG_URL
        assert catalogs[0].get_root() is client

    def test_get_catalogs_empty(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        requests_mock.get(REGISTRY_URL, json={"catalogs": [], "links": []})

        assert list(client.get_catalogs()) == []

    def test_get_catalogs_uses_catalogs_link(self, requests_mock: Mocker) -> None:
        root = root_dict(ALL_CLASSES, catalogs_link=False)
        registry_url = f"{ROOT_URL}/api/registry"
        root["links"].append(_link("catalogs", registry_url))
        requests_mock.get(ROOT_URL, json=root)
        requests_mock.get(registry_url, json={"catalogs": [], "links": []})

        list(Client.open(ROOT_URL).get_catalogs())

        assert requests_mock.request_history[-1].url == registry_url

    def test_get_catalogs_without_catalogs_link(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock, catalogs_link=False)
        requests_mock.get(REGISTRY_URL, json={"catalogs": [], "links": []})

        with pytest.warns(MissingLink, match="rel='catalogs'"):
            list(client.get_catalogs())

        assert requests_mock.request_history[-1].url == REGISTRY_URL

    def test_get_catalogs_warns_once_without_catalogs_link(
        self, requests_mock: Mocker
    ) -> None:
        client = _open_client(requests_mock, catalogs_link=False)
        catalogs = [catalog_dict(catalog_id) for catalog_id in ("a", "b", "c")]
        requests_mock.get(REGISTRY_URL, json={"catalogs": catalogs, "links": []})

        with pytest.warns(MissingLink) as record:
            list(client.get_catalogs())

        assert len(record) == 1

    def test_get_catalogs_uses_catalog_self_link(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        catalog = catalog_dict("forestry")
        self_href = f"{ROOT_URL}/tenants/forestry"
        catalog["links"][0] = _link("self", self_href)
        requests_mock.get(REGISTRY_URL, json={"catalogs": [catalog], "links": []})

        (forestry,) = client.get_catalogs()

        assert forestry.get_self_href() == self_href

    def test_get_catalogs_without_self_link_uses_registry(
        self, requests_mock: Mocker
    ) -> None:
        client = _open_client(requests_mock)
        catalog = catalog_dict("forestry")
        catalog["links"] = [link for link in catalog["links"] if link["rel"] != "self"]
        requests_mock.get(REGISTRY_URL, json={"catalogs": [catalog], "links": []})

        (forestry,) = client.get_catalogs()

        assert forestry.get_self_href() == CATALOG_URL

    def test_get_catalogs_from_catalog_lists_sub_catalogs(
        self, requests_mock: Mocker
    ) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.get(
            SUB_CATALOGS_URL, json={"catalogs": [catalog_dict("fire")], "links": []}
        )

        sub_catalogs = list(catalog.get_catalogs())

        assert requests_mock.request_history[-1].url == SUB_CATALOGS_URL
        assert [sub.id for sub in sub_catalogs] == ["fire"]
        assert sub_catalogs[0].get_self_href() == f"{REGISTRY_URL}/fire"
        assert sub_catalogs[0].get_root() is catalog.get_root()

    def test_get_catalog(self, requests_mock: Mocker) -> None:
        def sign(obj: Modifiable) -> None: ...

        client = _open_client(requests_mock, modifier=sign)
        requests_mock.get(CATALOG_URL, json=catalog_dict("forestry"))

        catalog = client.get_catalog("forestry")

        assert isinstance(catalog, CatalogClient)
        assert catalog.id == "forestry"
        assert catalog.get_self_href() == CATALOG_URL
        assert catalog.get_root() is client
        assert catalog.get_conforms_to() == client.get_conforms_to()
        assert catalog._stac_io is client._stac_io
        assert catalog.modifier is sign

    def test_get_catalog_from_catalog_uses_registry(
        self, requests_mock: Mocker
    ) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.get(f"{REGISTRY_URL}/fire", json=catalog_dict("fire"))

        other = catalog.get_catalog("fire")

        assert other is not None
        assert other.get_root() is catalog.get_root()
        assert requests_mock.request_history[-1].url == f"{REGISTRY_URL}/fire"

    def test_get_catalog_not_found(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        requests_mock.get(CATALOG_URL, status_code=404)

        assert client.get_catalog("forestry") is None

    def test_get_catalog_error(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        requests_mock.get(CATALOG_URL, status_code=500, text="nope")

        with pytest.raises(APIError, match="nope"):
            client.get_catalog("forestry")

    def test_get_catalog_requires_id(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)

        with pytest.raises(ValueError, match="A `catalog_id` must be provided"):
            client.get_catalog("")

    def test_get_catalog_encodes_id(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        url = f"{REGISTRY_URL}/a%2Fb"
        requests_mock.get(url, json=catalog_dict("a/b"))

        client.get_catalog("a/b")

        assert requests_mock.request_history[-1].url == url

    def test_get_catalog_uses_catalog_conforms_to(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(
            requests_mock, catalog_classes=("/core", "/collections")
        )

        assert catalog.get_conforms_to() == [_uri("/core"), _uri("/collections")]

    def test_get_catalogs_from_catalog_checks_api_root_conformance(
        self, requests_mock: Mocker
    ) -> None:
        catalog = _scoped_client(requests_mock, catalog_classes=("/core",))
        requests_mock.get(SUB_CATALOGS_URL, json={"catalogs": [], "links": []})

        assert list(catalog.get_catalogs()) == []

    @pytest.mark.parametrize(
        "read",
        [
            lambda client: list(client.get_catalogs()),
            lambda client: client.get_catalog("forestry"),
        ],
        ids=["get_catalogs", "get_catalog"],
    )
    def test_read_does_not_conform(
        self, requests_mock: Mocker, read: Callable[[Client], Any]
    ) -> None:
        client = _open_client(requests_mock, classes=())

        with pytest.raises(DoesNotConformTo, match="MULTI_TENANT_CATALOGS$"):
            read(client)

        assert requests_mock.request_history[-1].url == f"{ROOT_URL}/"


class TestScopedReads:
    def test_get_collections(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.get(
            SCOPED_COLLECTIONS_URL,
            json={
                "collections": [collection_dict("s2", SCOPED_COLLECTIONS_URL)],
                "links": [],
            },
        )

        collections = list(catalog.get_collections())

        assert [collection.id for collection in collections] == ["s2"]
        assert collections[0].get_root() is catalog

    def test_get_collection(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        url = f"{SCOPED_COLLECTIONS_URL}/s2"
        requests_mock.get(url, json=collection_dict("s2", SCOPED_COLLECTIONS_URL))

        collection = catalog.get_collection("s2")

        assert collection is not None
        assert requests_mock.request_history[-1].url == url

    def test_search(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        search_url = f"{CATALOG_URL}/search"
        requests_mock.post(
            search_url, json={"type": "FeatureCollection", "features": []}
        )

        list(catalog.search(collections=["s2"]).items())

        request = requests_mock.request_history[-1]
        assert request.url == search_url
        assert request.json()["collections"] == ["s2"]

    def test_search_requires_mtc_search(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock, classes=(MTC,))

        with pytest.raises(DoesNotConformTo, match="MULTI_TENANT_CATALOGS_SEARCH"):
            catalog.search()

    def test_get_items_without_mtc_search_falls_back(
        self, requests_mock: Mocker
    ) -> None:
        catalog = _scoped_client(requests_mock, classes=(MTC,))

        with pytest.warns(PystacClientWarning):
            assert list(catalog.get_items()) == []

    @pytest.mark.parametrize(
        "classes, search_url",
        [(ALL_CLASSES, f"{CATALOG_URL}/search"), ((MTC,), f"{ROOT_URL}/search")],
        ids=["scoped_search", "global_search"],
    )
    @pytest.mark.parametrize(
        "read",
        [
            lambda collection: list(collection.get_items("item-1")),
            lambda collection: collection.get_item("item-1"),
        ],
        ids=["get_items", "get_item"],
    )
    def test_collection_search_by_id(
        self,
        requests_mock: Mocker,
        classes: tuple[str, ...],
        search_url: str,
        read: Callable[[CollectionClient], Any],
    ) -> None:
        catalog = _scoped_client(
            requests_mock, classes, catalog_classes=("/collections", "/item-search")
        )
        requests_mock.get(
            f"{SCOPED_COLLECTIONS_URL}/s2",
            json=collection_dict("s2", SCOPED_COLLECTIONS_URL),
        )
        collection = catalog.get_collection("s2")
        assert isinstance(collection, CollectionClient)
        requests_mock.get(
            search_url, json={"type": "FeatureCollection", "features": []}
        )

        read(collection)

        assert requests_mock.request_history[-1].url.startswith(f"{search_url}?")

    def test_get_queryables_uses_catalog_conforms_to(
        self, requests_mock: Mocker
    ) -> None:
        catalog = _scoped_client(
            requests_mock,
            classes=(*ALL_CLASSES, "/item-search#filter"),
            catalog_classes=("/core",),
        )

        with pytest.raises(DoesNotConformTo, match="FILTER"):
            catalog.get_queryables()

    def test_get_queryables(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(
            requests_mock, catalog_classes=("/core", "/item-search#filter")
        )
        url = f"{CATALOG_URL}/queryables"
        requests_mock.get(url, json={"properties": {}})

        with pytest.warns(MissingLink):
            assert catalog.get_queryables() == {"properties": {}}
        assert requests_mock.request_history[-1].url == url

    def test_root_search_does_not_need_mtc_search(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock, classes=(MTC,))
        requests_mock.post(
            f"{ROOT_URL}/search", json={"type": "FeatureCollection", "features": []}
        )

        assert list(client.search().items()) == []


CATALOG_WRITES: dict[str, Callable[[CatalogClient], Any]] = {
    "create_catalog": lambda client: client.create_catalog(catalog_dict("fire")),
    "update_catalog": lambda client: client.update_catalog(catalog_dict("fire")),
    "delete_catalog": lambda client: client.delete_catalog("fire"),
    "link_catalog": lambda client: client.link_catalog("fire"),
    "unlink_catalog": lambda client: client.unlink_catalog("fire"),
    "link_collection": lambda client: client.link_collection("s2"),
    "unlink_collection": lambda client: client.unlink_collection("s2"),
    "create_collection": lambda client: client.create_collection(
        collection_dict("s2", SCOPED_COLLECTIONS_URL)
    ),
    "update_collection": lambda client: client.update_collection(
        collection_dict("s2", SCOPED_COLLECTIONS_URL)
    ),
}


class TestCatalogTransactions:
    def test_create_catalog(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        requests_mock.post(REGISTRY_URL, status_code=201, json=catalog_dict("fire"))

        catalog = client.create_catalog(
            pystac.Catalog("fire", "The fire catalog", href=f"{REGISTRY_URL}/fire")
        )

        request = requests_mock.request_history[-1]
        assert request.method == "POST"
        assert request.url == REGISTRY_URL
        assert request.json()["id"] == "fire"
        assert not any(link["rel"] == "self" for link in request.json()["links"])
        assert isinstance(catalog, CatalogClient)
        assert catalog.get_self_href() == f"{REGISTRY_URL}/fire"
        assert catalog.get_root() is client

    def test_create_sub_catalog(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.post(SUB_CATALOGS_URL, status_code=201, json=catalog_dict("fire"))

        sub_catalog = catalog.create_catalog(catalog_dict("fire"))

        assert requests_mock.request_history[-1].url == SUB_CATALOGS_URL
        assert sub_catalog is not None
        assert sub_catalog.get_self_href() == f"{REGISTRY_URL}/fire"

    @pytest.mark.parametrize(
        "status_code, response", [(201, ""), (202, '{"status": "Pending"}'), (204, "")]
    )
    def test_create_catalog_no_catalog_body(
        self, requests_mock: Mocker, status_code: int, response: str
    ) -> None:
        client = _open_client(requests_mock)
        requests_mock.post(REGISTRY_URL, status_code=status_code, text=response)

        assert client.create_catalog(catalog_dict("fire")) is None

    @pytest.mark.parametrize("catalog_id", [None, ""])
    def test_create_catalog_requires_id(
        self, requests_mock: Mocker, catalog_id: str | None
    ) -> None:
        client = _open_client(requests_mock)

        with pytest.raises(ValueError, match="A catalog `id` must be provided"):
            client.create_catalog({**catalog_dict("fire"), "id": catalog_id})

    @pytest.mark.parametrize(
        "create, link_method",
        [
            (lambda client: client.create_catalog({"id": "fire"}), "link_catalog"),
            (lambda client: client.create_collection({"id": "s2"}), "link_collection"),
        ],
        ids=["create_catalog", "create_collection"],
    )
    def test_create_rejects_link_body(
        self,
        requests_mock: Mocker,
        create: Callable[[CatalogClient], Any],
        link_method: str,
    ) -> None:
        catalog = _scoped_client(requests_mock)

        with pytest.raises(ValueError, match=f"Use `{link_method}`"):
            create(catalog)

        assert requests_mock.request_history[-1].method == "GET"

    @pytest.mark.parametrize(
        "create, url",
        [
            (lambda client: client.create_catalog({"id": "fire"}), REGISTRY_URL),
            (lambda client: client.create_collection({"id": "s2"}), COLLECTIONS_URL),
        ],
        ids=["create_catalog", "create_collection"],
    )
    def test_create_on_root_sends_id_only_body(
        self, requests_mock: Mocker, create: Callable[[Client], Any], url: str
    ) -> None:
        client = _open_client(requests_mock)
        requests_mock.post(url, status_code=400, text="invalid body")

        with pytest.raises(APIError, match="invalid body"):
            create(client)

        request = requests_mock.request_history[-1]
        assert request.url == url
        assert request.json().keys() == {"id"}

    def test_create_catalog_does_not_mutate_dict(self, requests_mock: Mocker) -> None:
        client = _open_client(requests_mock)
        body = catalog_dict("fire")
        requests_mock.post(REGISTRY_URL, status_code=201, text="")

        client.create_catalog(body)

        assert body == catalog_dict("fire")

    @pytest.mark.parametrize(
        "create",
        [
            lambda client: client.create_catalog({"id": "fire"}),
            lambda client: client.create_collection({"id": "s2"}),
        ],
        ids=["create_catalog", "create_collection"],
    )
    def test_create_link_body_checks_conformance_first(
        self, requests_mock: Mocker, create: Callable[[CatalogClient], Any]
    ) -> None:
        catalog = _scoped_client(requests_mock, classes=(MTC,))

        with pytest.raises(DoesNotConformTo, match="MULTI_TENANT_CATALOGS_TRANSACTION"):
            create(catalog)

    @pytest.mark.parametrize("status_code", [400, 401, 403, 409, 500])
    def test_create_catalog_error(
        self, requests_mock: Mocker, status_code: int
    ) -> None:
        client = _open_client(requests_mock)
        requests_mock.post(REGISTRY_URL, status_code=status_code, text="nope")

        with pytest.raises(APIError, match="nope") as excinfo:
            client.create_catalog(catalog_dict("fire"))

        assert excinfo.value.status_code == status_code

    @pytest.mark.parametrize("scoped", [False, True])
    def test_update_catalog(self, requests_mock: Mocker, scoped: bool) -> None:
        client = (_scoped_client if scoped else _open_client)(requests_mock)
        url = f"{REGISTRY_URL}/fire"
        requests_mock.put(url, json=catalog_dict("fire"))

        catalog = client.update_catalog(catalog_dict("fire"))

        request = requests_mock.request_history[-1]
        assert request.method == "PUT"
        assert request.url == url
        assert isinstance(catalog, CatalogClient)

    @pytest.mark.parametrize("scoped", [False, True])
    def test_delete_catalog(self, requests_mock: Mocker, scoped: bool) -> None:
        client = (_scoped_client if scoped else _open_client)(requests_mock)
        url = f"{REGISTRY_URL}/fire"
        requests_mock.delete(url, status_code=204)

        client.delete_catalog("fire")

        request = requests_mock.request_history[-1]
        assert request.method == "DELETE"
        assert request.url == url

    def test_link_catalog(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.post(SUB_CATALOGS_URL, status_code=200, json=catalog_dict("fire"))

        linked = catalog.link_catalog("fire")

        request = requests_mock.request_history[-1]
        assert request.url == SUB_CATALOGS_URL
        assert request.json() == {"id": "fire"}
        assert linked is not None
        assert linked.id == "fire"

    def test_link_catalog_not_found(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.post(SUB_CATALOGS_URL, status_code=404, text="no fire")

        with pytest.raises(APIError, match="no fire") as excinfo:
            catalog.link_catalog("fire")

        assert excinfo.value.status_code == 404

    def test_unlink_catalog(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        url = f"{SUB_CATALOGS_URL}/fire"
        requests_mock.delete(url, status_code=204)

        catalog.unlink_catalog("fire")

        request = requests_mock.request_history[-1]
        assert request.method == "DELETE"
        assert request.url == url

    def test_link_collection(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        requests_mock.post(
            SCOPED_COLLECTIONS_URL,
            status_code=200,
            json=collection_dict("s2", SCOPED_COLLECTIONS_URL),
        )

        collection = catalog.link_collection("s2")

        request = requests_mock.request_history[-1]
        assert request.url == SCOPED_COLLECTIONS_URL
        assert request.json() == {"id": "s2"}
        assert isinstance(collection, CollectionClient)
        assert collection.get_self_href() == f"{SCOPED_COLLECTIONS_URL}/s2"
        assert collection.get_root() is catalog

    def test_unlink_collection(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock)
        url = f"{SCOPED_COLLECTIONS_URL}/s2"
        requests_mock.delete(url, status_code=204)

        catalog.unlink_collection("s2")

        request = requests_mock.request_history[-1]
        assert request.method == "DELETE"
        assert request.url == url

    @pytest.mark.parametrize(
        "link",
        [
            lambda client: client.link_catalog(""),
            lambda client: client.unlink_catalog(""),
            lambda client: client.link_collection(""),
            lambda client: client.unlink_collection(""),
            lambda client: client.delete_catalog(""),
        ],
        ids=[
            "link_catalog",
            "unlink_catalog",
            "link_collection",
            "unlink_collection",
            "delete_catalog",
        ],
    )
    def test_write_requires_id(
        self, requests_mock: Mocker, link: Callable[[CatalogClient], Any]
    ) -> None:
        catalog = _scoped_client(requests_mock)

        with pytest.raises(ValueError, match="must be provided"):
            link(catalog)

        assert requests_mock.request_history[-1].method == "GET"

    @pytest.mark.parametrize("write", CATALOG_WRITES.values(), ids=CATALOG_WRITES)
    def test_write_does_not_conform(
        self, requests_mock: Mocker, write: Callable[[CatalogClient], Any]
    ) -> None:
        catalog = _scoped_client(
            requests_mock, classes=(MTC, MTC_SEARCH, COLLECTION_TRANSACTION)
        )

        with pytest.raises(DoesNotConformTo, match="MULTI_TENANT_CATALOGS_TRANSACTION"):
            write(catalog)

        assert requests_mock.request_history[-1].method == "GET"

    @pytest.mark.parametrize("write", CATALOG_WRITES.values(), ids=CATALOG_WRITES)
    def test_write_checks_api_root_conformance(
        self, requests_mock: Mocker, write: Callable[[CatalogClient], Any]
    ) -> None:
        catalog = _scoped_client(requests_mock, catalog_classes=("/core",))
        requests_mock.register_uri(ANY, ANY, status_code=204, text="")

        write(catalog)

        assert requests_mock.request_history[-1].method != "GET"

    @pytest.mark.parametrize("status_code", [204, 500])
    @pytest.mark.parametrize("write", CATALOG_WRITES.values(), ids=CATALOG_WRITES)
    def test_write_clears_get_collection_cache(
        self,
        requests_mock: Mocker,
        write: Callable[[CatalogClient], Any],
        status_code: int,
    ) -> None:
        catalog = _scoped_client(requests_mock)
        collection_url = f"{SCOPED_COLLECTIONS_URL}/s2"
        get_mock = requests_mock.get(
            collection_url, json=collection_dict("s2", SCOPED_COLLECTIONS_URL)
        )
        for url in (REGISTRY_URL, SUB_CATALOGS_URL, SCOPED_COLLECTIONS_URL):
            requests_mock.post(url, status_code=status_code, text="")
        for url in (f"{REGISTRY_URL}/fire", f"{SUB_CATALOGS_URL}/fire", collection_url):
            requests_mock.put(url, status_code=status_code, text="")
            requests_mock.delete(url, status_code=status_code)

        catalog.get_collection("s2")
        catalog.get_collection("s2")
        assert get_mock.call_count == 1

        error = (
            pytest.raises(APIError) if status_code >= 400 else contextlib.nullcontext()
        )
        with error:
            write(catalog)
        catalog.get_collection("s2")

        assert get_mock.call_count == 2


class TestScopedCollectionTransactions:
    def test_create_collection(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock, classes=(MTC, MTC_TRANSACTION))
        body = collection_dict("s2", SCOPED_COLLECTIONS_URL)
        requests_mock.post(SCOPED_COLLECTIONS_URL, status_code=201, json=body)

        collection = catalog.create_collection(body)

        assert requests_mock.request_history[-1].url == SCOPED_COLLECTIONS_URL
        assert isinstance(collection, CollectionClient)
        assert collection.get_self_href() == f"{SCOPED_COLLECTIONS_URL}/s2"

    def test_update_collection(self, requests_mock: Mocker) -> None:
        catalog = _scoped_client(requests_mock, classes=(MTC, MTC_TRANSACTION))
        url = f"{SCOPED_COLLECTIONS_URL}/s2"
        body = collection_dict("s2", SCOPED_COLLECTIONS_URL)
        requests_mock.put(url, json=body)

        catalog.update_collection(body)

        request = requests_mock.request_history[-1]
        assert request.method == "PUT"
        assert request.url == url

    @pytest.mark.parametrize(
        "write, method",
        [
            (lambda client: client.patch_collection("s2", {"title": "x"}), "PATCH"),
            (lambda client: client.delete_collection("s2"), "DELETE"),
        ],
        ids=["patch_collection", "delete_collection"],
    )
    def test_patch_and_delete_use_global_collection(
        self,
        requests_mock: Mocker,
        write: Callable[[CatalogClient], Any],
        method: str,
    ) -> None:
        catalog = _scoped_client(requests_mock)
        url = f"{COLLECTIONS_URL}/s2"
        requests_mock.register_uri(method, url, status_code=204)

        write(catalog)

        request = requests_mock.request_history[-1]
        assert request.method == method
        assert request.url == url

    def test_delete_collection_needs_collection_transaction(
        self, requests_mock: Mocker
    ) -> None:
        catalog = _scoped_client(requests_mock, classes=(MTC, MTC_TRANSACTION))

        with pytest.raises(DoesNotConformTo, match="^.*COLLECTION_TRANSACTION$"):
            catalog.delete_collection("s2")

    @pytest.mark.parametrize(
        "catalog_classes", [None, ("/collections",)], ids=["root", "catalog"]
    )
    def test_create_item_uses_global_items(
        self, requests_mock: Mocker, catalog_classes: tuple[str, ...] | None
    ) -> None:
        catalog = _scoped_client(
            requests_mock,
            classes=(*ALL_CLASSES, "/ogcapi-features/extensions/transaction"),
            catalog_classes=catalog_classes,
        )
        requests_mock.get(
            f"{SCOPED_COLLECTIONS_URL}/s2",
            json=collection_dict("s2", SCOPED_COLLECTIONS_URL),
        )
        collection = catalog.get_collection("s2")
        assert isinstance(collection, CollectionClient)
        items_url = f"{COLLECTIONS_URL}/s2/items"
        requests_mock.post(items_url, status_code=201, text="")

        collection.create_item({"type": "Feature", "id": "item-1"})

        assert requests_mock.request_history[-1].url == items_url
