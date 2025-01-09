from gelbooru_crawler import Crawler, UserInfo

import asyncio


user_info = UserInfo("", "")
crawler = Crawler(user_info)

TAGS = "blue_archive"

async def main():
    user_info = UserInfo("", "")
    crawler = Crawler(user_info)

    urls = await crawler.get_urls(TAGS, end_page=1)
    await crawler.download_images(urls=urls)
    
if __name__ == "__main__":
    asyncio.run(main())
