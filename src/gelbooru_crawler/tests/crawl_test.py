from gelbooru_crawler import Crawler, UserInfo

import asyncio


TAGS = "blue_archive"


async def main():
    user_info = UserInfo("", "")
    crawler = Crawler(user_info)

    urls = await crawler.get_urls(TAGS)
    print(urls)
    
asyncio.run(main())