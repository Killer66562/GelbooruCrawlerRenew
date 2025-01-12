import argparse
import asyncio
import dotenv

from gelbooru_crawler import Crawler, UserInfo


dotenv.load_dotenv(".env")

async def main():
    parser = argparse.ArgumentParser()

    parser.add_argument("--mode", type=str, choices=["get-urls", "download-images", "gui"])

    parser.add_argument("--tags", type=str, default="")
    parser.add_argument("--startPage", type=int, default=1)
    parser.add_argument("--endPage", type=int, default=200)
    parser.add_argument("--pageSize", type=int, default=100)
    parser.add_argument("--maxWorkers", type=int, default=100)

    parser.add_argument("--urls", type=list[str], nargs="*", default=[])
    parser.add_argument("--downloadFolder", type=str, default="images")
    parser.add_argument("--ignoreVideos", type=bool, default=True)
    parser.add_argument("--chunksize", type=int, default=4096)
    parser.add_argument("--asyncWrite", type=bool, default=True)

    args = parser.parse_args()

    user_id = dotenv.get_key(dotenv_path=".env", key_to_get="USER_ID")
    api_key = dotenv.get_key(dotenv_path=".env", key_to_get="API_KEY")

    user_info = UserInfo(user_id, api_key)
    crawler = Crawler(user_info)

    if args.mode == "gui":
        pass
    elif args.mode == "get-urls":
        urls = await crawler.get_urls(args.tags, args.startPage, args.endPage, args.pageSize)
    elif args.mode == "download-images":
        urls = ["".join(char_list) for char_list in args.urls]
        await crawler.download_images(urls, args.downloadFolder, ignore_videos=args.ignoreVideos, chunksize=args.chunksize, async_write=args.asyncWrite)
    else:
        raise ValueError("Please select a valid mode or start with gui.")

if __name__ == "__main__":
    asyncio.run(main=main())