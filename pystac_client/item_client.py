import logging
import os
from typing import TYPE_CHECKING, Iterable, Optional, cast, List, Union

import asyncio
import pystac
from pystac.link import Link
from pystac_client.conformance import ConformanceClasses
from pystac_client.exceptions import APIError
from pystac_client.item_search import ItemSearch
from pystac.layout import LayoutTemplate
from pystac_client.stac_api_io import StacApiIO
import fsspec


logger = logging.getLogger(__name__)


class ItemClient(pystac.Item):
    def __repr__(self) -> str:
        return "<ItemClient id={}>".format(self.id)

    @staticmethod
    async def download_file(source: Union[str, Link], filename: str, concurrent_downloads=3) -> None:
        url = source["href"] if isinstance(source, Link) else source
        ## TODO - dynamically determine fs
        fs = fsspec.filesystem("http", asynchronous=True)
        async with asyncio.Semaphore(concurrent_downloads):
            logger.debug(f"Downloading {url} to {filename}")
            await fs._get_file(url, filename)
            logger.debug(f"Downloaded {filename}")

    async def download_assets(
        self,
        assets: Optional[List[str]] = None,
        save_item: bool = True,
        overwrite: bool = False,
        path_template: str = "${collection}/${id}",
        concurrent_downloads: int = 3
    ) -> pystac.Item:

        _assets = self.assets.keys() if assets is None else assets

        # determine path from template and item
        layout = LayoutTemplate(path_template)
        path = layout.substitute(self)

        # make necessary directories
        os.makedirs(path, exist_ok=True)

        new_item = self.clone()

        tasks = []
        for a in _assets:
            if a not in self.assets:
                continue
            href = self.assets[a].href
            
            # get extension from asset href, strip parameters off if this is an API
            ext = os.path.splitext(href.split('?')[0])[-1]
            # new filename using asset key and extension
            new_href = os.path.join(path, a + ext)
            
            # save file
            if not os.path.exists(new_href) or overwrite:
                tasks.append(asyncio.create_task(self.download_file(href, new_href, concurrent_downloads=concurrent_downloads)))

            # update
            new_item.assets[a].href = new_href
        
        #async with sem:
        await asyncio.wait(tasks)
        
        # save Item metadata alongside saved assets
        if save_item:
            new_item.remove_links('root')
            new_item.save_object(dest_href=os.path.join(path, 'item.json'))
        
        return new_item
