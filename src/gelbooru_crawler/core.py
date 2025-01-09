from aiohttp import ClientSession
from asyncio import Semaphore
from datetime import datetime, timedelta, timezone

import time
import asyncio
import aiofiles
import pathlib
import os


class RequestInfo(object):
    def __init__(self, success: bool):
        self._success = success

    @property
    def success(self) -> bool:
        return self._success
    

class GetUrlsRequestInfo(RequestInfo):
    def __init__(self, success, urls: list[str]):
        super().__init__(success)
        self._urls = urls

    @property
    def urls(self) -> list[str]:
        return self._urls


class UserInfo(object):
    def __init__(self, user_id: str, api_key: str):
        self._user_id = user_id
        self._api_key = api_key

    @property
    def user_id(self) -> str:
        return self._user_id
    
    @property
    def api_key(self) -> str:
        return self._api_key


class Crawler(object):
    '''
    UMM
    '''
    BASE_URL = "https://gelbooru.com/index.php?"
    BASE_PARAMS = {
        'page': 'dapi', 
        's': 'post', 
        'q': 'index', 
        'json': 1
    }

    DEFAULT_MAX_WORKERS = 1000
    DEFAULT_MAX_RETRY_TIMES = 5
    DEFAULT_TIMEOUT_SECS = 10
    DEFAULT_RETRY_AFTER_SECS = 5

    DOWNLOAD_FOLDER_ROOT_PATH = "images"

    def __init__(self, user_info: UserInfo):
        self._user_info = user_info

        self._max_workers = self.DEFAULT_MAX_WORKERS
        self._max_retry_times = self.DEFAULT_MAX_RETRY_TIMES
        self._timeout_secs = self.DEFAULT_TIMEOUT_SECS
        self._retry_after_secs = self.DEFAULT_RETRY_AFTER_SECS

    @property
    def max_workers(self) -> int:
        return self._max_workers
    
    @max_workers.setter
    def max_workers(self, value: int) -> None:
        self._max_workers = max(1, value)
    
    @property
    def max_retry_times(self) -> int:
        return self._max_retry_times
    
    @max_retry_times.setter
    def max_retry_times(self, value: int) -> None:
        self._max_retry_times = value
    
    @property
    def timeout_secs(self) -> int:
        return self._timeout_secs
    
    @timeout_secs.setter
    def timeout_secs(self, value: int) -> None:
        self._timeout_secs = value
    
    @property
    def retry_after_secs(self) -> int:
        return self._retry_after_secs
    
    @retry_after_secs.setter
    def retry_after_secs(self, value: int) -> None:
        self._retry_after_secs = value

    def _get_auth_params(self) -> dict[str, str]:
        return {
            'api_key': self._user_info.api_key, 
            'user_id': self._user_info.user_id
        }
    
    def _get_search_params(self, page: int, size: int, tags: str):
        return {
            'limit': size, 
            'tags': tags, 
            'pid': page
        }
    
    def _get_params_str(self, params: dict) -> str:
        return "&".join(("%s=%s" % (key, value) for key, value in params.items()))

    async def _get_urls_single_page(self, session: ClientSession, semaphore: Semaphore, page_url: str):
        for current_retry_times in range(self._max_retry_times):
            try:
                print(f"Crawling url: {page_url} (Retry: {current_retry_times})")
                async with semaphore:
                    response = await session.get(page_url, timeout=self._timeout_secs)
                print(f"Success on crawling url: {page_url}")

                try:
                    content = await response.json()
                    image_infos = content.get("post")

                    if not image_infos:
                        image_infos = []

                    urls = []

                    for image_info in image_infos:
                        image_url = image_info.get("file_url")
                        if not image_url:
                            continue
                        urls.append(image_url)
                    
                    return GetUrlsRequestInfo(success=True, urls=urls)
                except KeyboardInterrupt:
                    print("Interrupted by user")
                    return GetUrlsRequestInfo(success=False, urls=[])
                except:
                    print(f"Cannot get image urls from url: {page_url}")
                    return GetUrlsRequestInfo(success=False, urls=[])
            except KeyboardInterrupt:
                print("Interrupted by user")
                return GetUrlsRequestInfo(success=False, urls=[])
            except Exception:
                print(f"Failed on crawling url: {page_url}")
                if current_retry_times < self._max_retry_times - 1:
                    print(f"Retry after {self._retry_after_secs} secs")
                    await asyncio.sleep(self._retry_after_secs)
                
        return GetUrlsRequestInfo(success=False, urls=[])
            

    async def get_urls(self, tags: str, start_page: int = 1, end_page: int = 200, page_size: int = 100) -> list[str]:
        fixed_start_page = min(start_page, end_page)
        fixed_end_page = max(start_page, end_page)

        semaphore = Semaphore(self._max_workers)
        params_list = [self.BASE_PARAMS | self._get_auth_params() | self._get_search_params(page, page_size, tags) for page in range(fixed_start_page, fixed_end_page + 1)]
        params_strs = [self._get_params_str(params) for params in params_list]
        page_urls = [self.BASE_URL + params_str for params_str in params_strs]

        async with ClientSession() as session:
            tasks = [self._get_urls_single_page(session, semaphore, page_url) for page_url in page_urls]
            request_infos = await asyncio.gather(*tasks)
            
        urls_lists = [request_info.urls for request_info in request_infos if request_info.success]

        urls = []

        for urls_list in urls_lists:
            for url in urls_list:
                urls.append(url)

        return urls
    
    async def _download_single_image(self, session: ClientSession, semaphore: Semaphore, download_folder: str, url: str, chunksize: int = 4096, async_write: bool = True) -> RequestInfo:
        filename = url.split("/")[-1]
        filepath = pathlib.Path(download_folder, filename)

        for current_retry_times in range(self._max_retry_times):
            try:
                async with semaphore:
                    print(f"Downloading image, url: {url} (Retry={current_retry_times})")
                    response = await session.get(url)

                async with response:
                    if response.status == 200:
                        if async_write:
                            async with aiofiles.open(filepath, mode="wb") as file:
                                async for chunk in response.content.iter_chunked(chunksize):
                                    await file.write(chunk)
                        else:
                            with open(filepath, mode="wb") as file:
                                async for chunk in response.content.iter_chunked(chunksize):
                                    file.write(chunk)
                    else:
                        raise Exception()

                print(f"Download done, url: {url}")
                return RequestInfo(success=True)
            except KeyboardInterrupt:
                print("Interrupted by user")
                return RequestInfo(success=False)
            except Exception:
                print(f"Failed on downloading image, url: {url}")
                if current_retry_times < self._max_retry_times - 1:
                    print(f"Retry after {self._retry_after_secs} secs")

                    await asyncio.sleep(self._retry_after_secs)

        return RequestInfo(success=False)


    async def download_images(self, urls: list[str], download_folder: str | None = None, ignore_videos: bool = True, chunksize: int = 4096, async_write: bool = True) -> None:
        if ignore_videos is True:
            real_urls = [url for url in urls if not url.endswith("mp4")]
        else:
            real_urls = [url for url in urls]

        if not download_folder:
            if not os.path.exists(self.DOWNLOAD_FOLDER_ROOT_PATH):
                os.mkdir(self.DOWNLOAD_FOLDER_ROOT_PATH)

            ctime_str = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d%H%M%S")
            download_folder_path = pathlib.Path(self.DOWNLOAD_FOLDER_ROOT_PATH, ctime_str)
        else:
            download_folder_path = pathlib.Path(download_folder)

        download_folder_abs_path = os.path.abspath(download_folder_path)

        if not os.path.exists(download_folder_abs_path):
            os.mkdir(download_folder_abs_path)

        semaphore = Semaphore(self._max_workers)

        time_start = time.time()

        print("Start downloading image")
        async with ClientSession() as session:
            tasks = [self._download_single_image(session, semaphore, download_folder_abs_path, url, chunksize, async_write) for url in real_urls]
            results = await asyncio.gather(*tasks)

        success_list = [result for result in results if result.success is True]
        failed_list = [result for result in results if result.success is not True]

        success_count = len(success_list)
        failed_count = len(failed_list)

        print("All tasks are done")
        print(f"Successed tasks: {success_count}")
        print(f"Failed tasks: {failed_count}")

        time_end = time.time()
        time_delta = time_end - time_start

        print(f"Required time: {time_delta:<.4} secs")