import asyncio
import dataclasses
import enum
import logging
import re
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from pathlib import Path
from typing import Optional, Callable, Any
from urllib import parse

import aiohttp
import aiohttp.log
import xspf_lib as xspf
from aiohttp import web
from bs4 import BeautifulSoup


@dataclasses.dataclass(frozen=True)
class VideoPost:
    post_id: str
    title: str
    order: int | None
    datetime: str
    category_id: str
    video_id: str
    thumbnails_server: str
    api_data: str
    next_post_id: str | None


@dataclasses.dataclass(frozen=True)
class VideoCategory:
    category_id: str
    title: str
    posts: list[VideoPost]


@dataclasses.dataclass(frozen=True)
class Video:
    url: str
    type: str
    cookies: SimpleCookie
    expire: int


class Anime1API:
    _MAIN_HOST: str = "anime1.me"
    _MAIN_URL: str = f"https://{_MAIN_HOST}"
    _API_URL: str = f"https://v.{_MAIN_HOST}/api"
    _USER_AGENT: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36"
    _CATEGORY_ID_PATTERN: re.Pattern = re.compile(r"'categoryID':\s'(.*?)'")
    _POST_ORDER_PATTERN: re.Pattern = re.compile(r".*?\[(\d+)]")
    _PROXY_EXPIRE_OFFSET_SECONDS: int = 5

    def __init__(self):
        self._cookies: aiohttp.CookieJar = aiohttp.CookieJar()
        self._client: aiohttp.ClientSession = aiohttp.ClientSession(raise_for_status=True, cookie_jar=self._cookies)

    @staticmethod
    def _get_page_headers() -> dict[str, str]:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Referer": Anime1API._MAIN_URL + "/",
            "User-Agent": Anime1API._USER_AGENT,
        }

    @staticmethod
    def _get_api_headers() -> dict[str, str]:
        return {
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Pragma": "no-cache",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": Anime1API._MAIN_URL,
            "Referer": Anime1API._MAIN_URL + "/",
            "User-Agent": Anime1API._USER_AGENT,
        }

    @staticmethod
    def _get_video_headers(bytes_range: str | None, bytes_if_range: str | None) -> dict[str, str]:
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity;q=1, *;q=0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": Anime1API._MAIN_URL + "/",
            "User-Agent": Anime1API._USER_AGENT,
        }
        if bytes_range is not None:
            headers["Range"] = bytes_range
        if bytes_if_range is not None:
            headers["If-Range"] = bytes_if_range
        return headers

    @staticmethod
    def _parse_video_posts(soup: BeautifulSoup) -> list[VideoPost]:
        articles = soup.find_all("article", id=True)
        posts: list[VideoPost] = list()
        all_has_order = True
        for article in articles:
            header_element = article.find("header")
            content_element = article.find("div", attrs={"class": "entry-content"})
            content_element_p = content_element.find("p")
            video_element = content_element.find("video", id=True)
            all_posts_element = content_element_p.find("a", string="全集連結")
            next_post_element = content_element_p.find("a", string="下一集")

            post_title = header_element.find("h2").text
            order_match = Anime1API._POST_ORDER_PATTERN.match(post_title)
            order = int(order_match.group(1)) if order_match is not None else None
            if order is None:
                all_has_order = False

            post = VideoPost(
                post_id=article["id"].split("-")[1],
                title=post_title,
                order=order,
                datetime=header_element.find("time")["datetime"],
                category_id=all_posts_element["href"].split("=")[1],
                video_id=video_element["data-vid"],
                thumbnails_server=video_element["data-tserver"],
                api_data=parse.unquote(video_element["data-apireq"]),
                next_post_id=next_post_element["href"].split("=")[1] if next_post_element is not None else None
            )
            posts.append(post)
        if all_has_order:
            posts.sort(key=lambda i: i.order)
        else:
            posts.reverse()
        return posts

    @staticmethod
    def _is_category(soup: BeautifulSoup) -> bool:
        body_classes = soup.find("body", attrs={"class": True})["class"]
        return "category" in body_classes

    @staticmethod
    def _is_single_post(soup: BeautifulSoup) -> bool:
        body_classes = soup.find("body", attrs={"class": True})["class"]
        return "single-post" in body_classes

    @staticmethod
    def _parse_category(soup: BeautifulSoup) -> VideoCategory:
        first_script_text = soup.find("script").text
        category_id = Anime1API._CATEGORY_ID_PATTERN.search(first_script_text).group(1)
        category_title = soup.find("header", attrs={"class": "page-header"}).find("h1", attrs={"class": "page-title"}).text
        posts = Anime1API._parse_video_posts(soup)

        return VideoCategory(
            category_id=category_id,
            title=category_title,
            posts=posts
        )

    @staticmethod
    def _parse_single_post(soup: BeautifulSoup) -> VideoPost | None:
        posts = Anime1API._parse_video_posts(soup)
        return posts[0] if len(posts) > 0 else None

    @staticmethod
    def is_valid_posts_url(url: str) -> bool:
        # noinspection PyBroadException
        try:
            return parse.urlparse(url).hostname.endswith(Anime1API._MAIN_HOST)
        except Exception:
            return False

    async def get_video_posts(self, url: str) -> VideoPost | VideoCategory | None:
        async with self._client.get(url, headers=self._get_page_headers()) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
            if self._is_category(soup):
                return self._parse_category(soup)
            elif self._is_single_post(soup):
                return self._parse_single_post(soup)
            else:
                return None

    async def get_video_post(self, post_id: str) -> VideoPost | None:
        url = self._MAIN_URL + "/" + post_id
        async with self._client.get(url, headers=self._get_page_headers()) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
            return self._parse_single_post(soup) if self._is_single_post(soup) else None

    async def get_video_category(self, category_id: str) -> VideoCategory | None:
        url = self._MAIN_URL + "/?" + parse.urlencode({"cat": category_id})
        async with self._client.get(url, headers=self._get_page_headers()) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
            return self._parse_category(soup) if self._is_category(soup) else None

    async def _get_video(self, api_data: str) -> Video:
        data = {"d": api_data}
        scheme = parse.urlparse(self._API_URL).scheme
        async with self._client.post(self._API_URL, headers=self._get_api_headers(), data=data) as r:
            content = (await r.json())["s"][0]
            expire = int(r.cookies["e"].value) - self._PROXY_EXPIRE_OFFSET_SECONDS
            return Video(
                url=scheme + ":" + content["src"],
                type=content["type"],
                cookies=r.cookies,
                expire=expire
            )

    async def get_video(self, post: VideoPost) -> Video:
        return await self._get_video(post.api_data)

    async def get_video_by_post_id(self, post_id: str) -> Video | None:
        post = await self.get_video_post(post_id)
        return await self.get_video(post) if post is not None else None

    def open_video(self, video: Video, bytes_range: str | None, bytes_if_range: str | None):
        headers = self._get_video_headers(bytes_range, bytes_if_range)
        return self._client.get(video.url, headers=headers)

    async def close(self):
        await self._client.close()


@enum.unique
class PlaylistType(enum.Enum):
    M3U8 = enum.auto()
    DPL = enum.auto()
    DPL_EXT = enum.auto()
    XSPF = enum.auto()
    XSPF_EXT = enum.auto()


@dataclasses.dataclass(frozen=True)
class PlaylistInfo:
    playlist_type: PlaylistType
    content: str
    content_type: str
    file_name: str


class Anime1Server:
    _INSTANCE: Optional['Anime1Server'] = None
    _CACHE_CLEAN_SIZE: int = 128

    def __init__(self):
        self._api = Anime1API()
        self._video_cache: dict[str, Video] = dict()

    @staticmethod
    async def instance() -> 'Anime1Server':
        if Anime1Server._INSTANCE is None:
            Anime1Server._INSTANCE = Anime1Server()
        return Anime1Server._INSTANCE

    @staticmethod
    def _build_m3u8(base_uri: str, category: VideoCategory) -> str:
        content = "#EXTM3U" + "\n"
        base_uri = base_uri.rstrip('/')
        for post in category.posts:
            content += f"#EXTINF:-1,{post.title}" + "\n"
            content += f"{base_uri}/v/{post.post_id}" + "\n"
        return content

    # noinspection SpellCheckingInspection
    @staticmethod
    def _build_dpl(base_uri: str, category: VideoCategory) -> str:
        content = "DAUMPLAYLIST" + "\n"
        content += "topindex=0" + "\n"
        content += "saveplaypos=0" + "\n"
        base_uri = base_uri.rstrip('/')
        for i, post in enumerate(category.posts):
            content += f"{i + 1}*title*{post.title}" + "\n"
            content += f"{i + 1}*file*{base_uri}/v/{post.post_id}" + "\n"
        return content

    # noinspection SpellCheckingInspection
    @staticmethod
    def _build_dpl_ext(base_uri: str, category: VideoCategory) -> str:
        content = "DAUMPLAYLIST" + "\n"
        content += "topindex=0" + "\n"
        content += "saveplaypos=0" + "\n"
        content += f"extplaylist={base_uri}/c/{category.category_id}/m3u8" + "\n"
        return content

    @staticmethod
    def _build_xspf(base_uri: str, category: VideoCategory) -> str:
        base_uri = base_uri.rstrip('/')
        content = xspf.Playlist(
            title=category.title,
            trackList=[
                xspf.Track(
                    location=f"{base_uri}/v/{post.post_id}",
                    title=post.title
                )
                for post in category.posts
            ]
        )
        return content.xml_string()

    @staticmethod
    def _build_xspf_ext(base_uri: str, category: VideoCategory) -> str:
        base_uri = base_uri.rstrip('/')
        content = xspf.Playlist(
            title=category.title,
            trackList=[
                xspf.Track(
                    location=f"{base_uri}/c/{category.category_id}",
                    title=category.title
                )
            ]
        )
        return content.xml_string()

    async def parse_url(self, base_uri: str, url: str) -> dict:
        if not self._api.is_valid_posts_url(url):
            raise ValueError("Invalid url")
        result = await self._api.get_video_posts(url)
        base_uri = base_uri.rstrip("/")
        if result is None:
            raise ValueError("Unknown url type")
        elif isinstance(result, VideoPost):
            return {
                "type": "single",
                "id": result.post_id,
                "title": result.title,
                "category": result.category_id,
                "url": f"{base_uri}/v/{result.post_id}"
            }
        elif isinstance(result, VideoCategory):
            return {
                "type": "category",
                "id": result.category_id,
                "title": result.title,
                "url": f"{base_uri}/c/{result.category_id}",
                "playlists": {
                    i.name.lower(): f"{base_uri}/c/{result.category_id}?playlist={i.name.lower()}"
                    for i in PlaylistType
                },
                "videos": [
                    {
                        "id": i.post_id,
                        "title": i.title,
                        "url": f"{base_uri}/v/{i.post_id}"
                    }
                    for i in result.posts
                ]
            }
        else:
            raise ValueError("Unknown parse type!")

    @staticmethod
    def _parse_playlist_type(playlist_type: str) -> PlaylistType:
        try:
            return PlaylistType[playlist_type.strip().upper()]
        except Exception:
            raise ValueError(f"Unknown playlist type {playlist_type}")

    async def get_category_playlist(self, base_uri: str, category_id: str, playlist_type: str | None) -> PlaylistInfo:
        playlist = self._parse_playlist_type(playlist_type) if playlist_type is not None else PlaylistType.M3U8
        category = await self._api.get_video_category(category_id)
        if category is None:
            raise ValueError("Unknown category")
        if playlist == PlaylistType.M3U8:
            return PlaylistInfo(
                playlist_type=playlist,
                content=self._build_m3u8(base_uri, category),
                content_type="application/x-mpegURL",
                file_name=f"{category.title}.m3u8"
            )
        elif playlist == PlaylistType.DPL:
            return PlaylistInfo(
                playlist_type=playlist,
                content=self._build_dpl(base_uri, category),
                content_type="text/plain",
                file_name=f"{category.title}.dpl"
            )
        elif playlist == PlaylistType.DPL_EXT:
            return PlaylistInfo(
                playlist_type=playlist,
                content=self._build_dpl_ext(base_uri, category),
                content_type="text/plain",
                file_name=f"{category.title}.dpl"
            )
        elif playlist == PlaylistType.XSPF:
            return PlaylistInfo(
                playlist_type=playlist,
                content=self._build_xspf(base_uri, category),
                content_type="application/xspf+xml",
                file_name=f"{category.title}.xspf"
            )
        elif playlist == PlaylistType.XSPF_EXT:
            return PlaylistInfo(
                playlist_type=playlist,
                content=self._build_xspf_ext(base_uri, category),
                content_type="application/xspf+xml",
                file_name=f"{category.title}.xspf"
            )
        else:
            raise ValueError(f"Unhandled playlist type {playlist}")

    async def _get_video(self, post_id: str) -> Video:
        current_time = time.time()
        video = None
        if post_id in self._video_cache:
            video = self._video_cache[post_id]
            if video.expire <= current_time:
                video = None
                del self._video_cache[post_id]
        if video is None:
            video = await self._api.get_video_by_post_id(post_id)
            if video is None:
                raise ValueError("Unknown video")
            self._video_cache[post_id] = video
        if len(self._video_cache) > self._CACHE_CLEAN_SIZE:
            for k, v in self._video_cache.items():
                if v.expire >= current_time:
                    del self._video_cache[k]
        return video

    async def open_video(self, post_id: str, bytes_range: str | None, bytes_if_range: str | None):
        video = await self._get_video(post_id)
        return self._api.open_video(video, bytes_range, bytes_if_range)


# noinspection PyMethodMayBeStatic
def main_routes() -> web.RouteTableDef:
    routes = web.RouteTableDef()

    def get_base_uri(request: web.Request) -> str:
        return str(request.url.origin()).rstrip("/")

    def get_query(request: web.Request, name: str, must_exists: bool = True, convert: Callable[[str], Any] = str) -> Any | None:
        if name in request.query:
            value = request.query[name]
            try:
                return convert(value)
            except Exception as e:
                raise web.HTTPBadRequest(reason=f"Query '{name}' parse error: {e}")
        elif must_exists:
            raise web.HTTPBadRequest(reason=f"Missing query '{name}'")
        else:
            return None

    def get_header(request: web.Request, name: str, must_exists: bool = True) -> str | None:
        if name in request.headers:
            return request.headers[name]
        elif must_exists:
            raise web.HTTPBadRequest(reason=f"Missing header '{name}'")
        else:
            return None

    @routes.get("/")
    async def index(request: web.Request) -> web.Response:
        base_uri = get_base_uri(request)
        return web.Response(body=f"Use {base_uri}/p?url=<Url> to parse any valid video posts url", status=HTTPStatus.OK)

    @routes.get(path="/p")
    async def parser(request: web.Request) -> web.Response:
        base_uri = get_base_uri(request)
        url = get_query(request, "url")
        try:
            anime = await Anime1Server.instance()
            result = await anime.parse_url(base_uri, url)
            return web.json_response(result)
        except aiohttp.ClientResponseError as e:
            return web.Response(status=e.status, reason=e.message)
        except aiohttp.ClientConnectorError as e:
            raise web.HTTPServiceUnavailable(reason=e.strerror)
        except Exception as e:
            raise web.HTTPInternalServerError(reason=str(e))

    @routes.get("/c/{category_id}")
    async def category(request: web.Request) -> web.Response:
        base_uri = get_base_uri(request)
        category_id = request.match_info["category_id"]
        playlist: str | None = get_query(request, "playlist", must_exists=False)
        try:
            anime = await Anime1Server.instance()
            result = await anime.get_category_playlist(base_uri, category_id, playlist)
            if playlist is None:
                return web.json_response(result.content)
            else:
                return web.json_response(
                    data=result.content,
                    headers={
                        "Content-Disposition": f"attachment; filename=\"{parse.quote(result.file_name)}\""
                    } if playlist is not None else None,
                    content_type=result.content_type
                )
        except aiohttp.ClientResponseError as e:
            return web.Response(status=e.status, reason=e.message)
        except aiohttp.ClientConnectorError as e:
            raise web.HTTPServiceUnavailable(reason=e.strerror)
        except Exception as e:
            raise web.HTTPInternalServerError(reason=str(e))

    @routes.get("/v/{post_id}")
    async def video(request: web.Request) -> web.StreamResponse:
        post_id = request.match_info["post_id"]
        header_range: str | None = get_header(request, "range", must_exists=False)
        header_if_range: str | None = get_header(request, "if_range", must_exists=False)
        try:
            anime = await Anime1Server.instance()
            async with await anime.open_video(post_id, header_range, header_if_range) as video_response:
                headers = {
                    k: video_response.headers[k]
                    for k in ["Content-Length", "Content-Range", "Etag", "Last-Modified"]
                    if k in video_response.headers
                }
                response = web.StreamResponse(status=HTTPStatus.PARTIAL_CONTENT, headers=headers)
                response.content_type = video_response.content_type
                await response.prepare(request)
                async for chunk in video_response.content.iter_any():
                    await response.write(chunk)
            await response.write_eof()
            return response
        except aiohttp.ClientResponseError as e:
            return web.Response(status=e.status, reason=e.message)
        except aiohttp.ClientConnectorError as e:
            raise web.HTTPServiceUnavailable(reason=e.strerror)
        except Exception as e:
            raise web.HTTPInternalServerError(reason=str(e))

    return routes


def setup_logger(logger: logging.Logger, name: str, log_dir: Optional[Path], debug: bool) -> logging.Logger:
    if debug:
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.StreamHandler())
    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.FileHandler(filename=log_dir.joinpath(f"{name}.log"), encoding="utf-8"))
    return logger


def launch_server(host: str, port: int, log_dir: Optional[Path] = None, debug: bool = False):
    async def on_response_prepare(_, response: web.StreamResponse):
        del response.headers["Server"]

    web_logger = setup_logger(aiohttp.log.web_logger, "web", log_dir, debug)
    app = web.Application(logger=web_logger)
    app.on_response_prepare.append(on_response_prepare)
    app.add_routes(main_routes())
    loop = asyncio.new_event_loop()
    loop.set_debug(debug)
    access_logger = setup_logger(aiohttp.log.access_logger, "access", log_dir, debug)
    web.run_app(
        app=app,
        host=host,
        port=port,
        access_log=access_logger,
        loop=loop
    )


if __name__ == "__main__":
    try:
        launch_server("127.0.0.1", 8520, None, True)
    except KeyboardInterrupt:
        pass
