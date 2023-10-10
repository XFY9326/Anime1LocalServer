import dataclasses
import re
import time
from http.cookies import SimpleCookie
from typing import Annotated
from urllib import parse

import aiohttp
import m3u8
import uvicorn
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from fastapi import FastAPI, Request, Response, Header, BackgroundTasks, HTTPException, status
from fastapi.responses import StreamingResponse


@dataclasses.dataclass(frozen=True)
class Episode:
    episode_id: str
    title: str
    datetime: str
    category: str
    video_id: str
    thumbnails_server: str
    api_data: str
    next_episode_id: str | None


@dataclasses.dataclass(frozen=True)
class Series:
    title: str
    category_id: str
    episode_ids: list[str]
    episodes: dict[str, Episode]


@dataclasses.dataclass(frozen=True)
class Video:
    url: str
    type: str
    cookies: SimpleCookie
    expire: int


class Anime:
    _INSTANCE: 'Anime' = None
    _MAIN_URL: str = "https://anime1.me/"
    _API_URL: str = "https://v.anime1.me/api"
    _USER_AGENT: str = UserAgent().chrome
    _CATEGORY_ID_PATTERN: re.Pattern = re.compile(r"'categoryID':\s'(.*?)'")
    _PROXY_EXPIRE_SECONDS: int = 5

    def __init__(self):
        self._cookies: aiohttp.CookieJar = aiohttp.CookieJar()
        self._client: aiohttp.ClientSession = aiohttp.ClientSession(raise_for_status=True, cookie_jar=self._cookies)
        self._series_cache: dict[str, Series] = dict()
        self._video_cache: dict[str, Video] = dict()

    @staticmethod
    async def instance() -> 'Anime':
        if Anime._INSTANCE is None:
            Anime._INSTANCE = Anime()
        return Anime._INSTANCE

    @staticmethod
    def _get_category_headers() -> dict[str, str]:
        return {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Cache-Control": "max-age=0",
            "Referer": "https://anime1.me/",
            "User-Agent": Anime._USER_AGENT,
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
            "Origin": "https://anime1.me",
            "Referer": "https://anime1.me/",
            "User-Agent": Anime._USER_AGENT,
        }

    @staticmethod
    def _get_video_header(header_range: str | None, header_if_range: str | None) -> dict[str, str]:
        headers = {
            "Accept": "*/*",
            "Accept-Encoding": "identity;q=1, *;q=0",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
            "Referer": "https://anime1.me/",
            "User-Agent": Anime._USER_AGENT,
        }
        if header_range is not None:
            headers["Range"] = header_range
        if header_if_range is not None:
            headers["If-Range"] = header_if_range
        return headers

    async def _get_series(self, url: str) -> Series:
        async with self._client.get(url, headers=self._get_category_headers()) as r:
            soup = BeautifulSoup(await r.text(), "html.parser")
            body_classes = soup.find("body", attrs={"class": True})["class"]
            if "category" not in body_classes:
                raise aiohttp.ClientResponseError(request_info=r.request_info, history=r.history, status=status.HTTP_404_NOT_FOUND, message="Not a category page")

            first_script_text = soup.find("script").text
            category_id_match = self._CATEGORY_ID_PATTERN.search(first_script_text)
            if category_id_match is None:
                raise aiohttp.ClientResponseError(request_info=r.request_info, history=r.history, status=status.HTTP_404_NOT_FOUND, message="Category ID not found")
            else:
                category_id = category_id_match.group(1)

        articles = soup.find_all("article", id=True)
        episodes: dict[str, Episode] = dict()
        episode_ids: list[str] = list()
        category_title = soup.find("h1", attrs={"class": "page-title"}).text
        for article in articles:
            header_element = article.find("header")
            content_element = article.find("div", attrs={"class": "entry-content"})
            content_element_p = content_element.find("p")
            video_element = content_element.find("video", id=True)
            next_episode_element = content_element_p.find("a", string="下一集")

            episode = Episode(
                episode_id=article["id"].split("-")[1],
                title=header_element.find("h2").text,
                datetime=header_element.find("time")["datetime"],
                category=category_id,
                video_id=video_element["data-vid"],
                thumbnails_server=video_element["data-tserver"],
                api_data=parse.unquote(video_element["data-apireq"]),
                next_episode_id=next_episode_element["href"].split("=")[1] if next_episode_element is not None else None
            )

            episodes[episode.episode_id] = episode
            episode_ids.append(episode.episode_id)
        episode_ids.reverse()
        return Series(
            title=category_title,
            category_id=category_id,
            episode_ids=episode_ids,
            episodes=episodes
        )

    async def _get_video(self, ep: Episode) -> Video:
        data = {"d": ep.api_data}
        scheme = parse.urlparse(self._API_URL).scheme
        async with self._client.post(self._API_URL, headers=self._get_api_headers(), data=data) as r:
            content = (await r.json())["s"][0]
            expire = int(r.cookies["e"].value) - self._PROXY_EXPIRE_SECONDS
            return Video(
                url=scheme + ":" + content["src"],
                type=content["type"],
                cookies=r.cookies,
                expire=expire
            )

    async def get_series(self, category_url: str) -> Series:
        series = await self._get_series(category_url)
        if series.category_id is not None:
            self._series_cache[series.category_id] = series
        return series

    async def get_series_by_id(self, category_id: str) -> Series:
        return await self.get_series(self._MAIN_URL + "?" + parse.urlencode({"cat": category_id}))

    async def get_video(self, category_id: str, episode_id: str) -> Video | None:
        if category_id in self._series_cache:
            series = self._series_cache[category_id]
        else:
            series = await self.get_series_by_id(category_id)
        if episode_id in series.episodes:
            episode = series.episodes[episode_id]
            if episode.episode_id in self._video_cache:
                video = self._video_cache[episode.episode_id]
                if video.expire < time.time():
                    return video
                else:
                    del self._video_cache[episode.episode_id]
            video = await self._get_video(episode)
            self._video_cache[episode.episode_id] = video
            return video
        else:
            return None

    async def open_video(self, video: Video, bytes_range: str | None, bytes_if_range: str | None) -> aiohttp.ClientResponse:
        return await self._client.get(video.url, headers=self._get_video_header(bytes_range, bytes_if_range))

    async def close(self):
        await self._client.close()


def episodes_to_playlist(base_uri: str, series: Series) -> str:
    content = m3u8.M3U8()
    for episode_id in series.episode_ids:
        episode = series.episodes[episode_id]
        segment = m3u8.Segment(uri=f"{base_uri.rstrip('/')}/v/{series.category_id}/{episode_id}", title=episode.title, duration=-1)
        content.add_segment(segment)
    return content.dumps()


app = FastAPI()


@app.get("/")
async def home(request: Request) -> Response:
    base_url = str(request.base_url).rstrip("/")
    return Response(content=f"Use {base_url}/parse?url=<CategoryUrl> instead!", status_code=status.HTTP_200_OK)


@app.get("/parse")
async def parse_url(url: str, request: Request) -> dict:
    anime = await Anime.instance()
    try:
        series = await anime.get_series(url)
        base_url = str(request.base_url).rstrip("/")
        return {
            "title": series.title,
            "series": f"{base_url}/v/{series.category_id}",
            "episodes": [
                {
                    "title": series.episodes[i].title,
                    "url": f"{base_url}/v/{series.category_id}/{i}"
                }
                for i in series.episode_ids
            ]
        }
    except aiohttp.ClientResponseError as e:
        raise HTTPException(e.status, detail=e.message)
    except aiohttp.ClientConnectorError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.strerror)


@app.get("/v/{category_id}")
async def video_series(category_id: str, request: Request) -> Response:
    anime = await Anime.instance()
    try:
        series = await anime.get_series_by_id(category_id)
        m3u8_content = episodes_to_playlist(str(request.base_url), series)
        return Response(content=m3u8_content, media_type="application/x-mpegURL")
    except aiohttp.ClientResponseError as e:
        raise HTTPException(e.status, detail=e.message)
    except aiohttp.ClientConnectorError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.strerror)


# noinspection PyShadowingBuiltins
@app.get("/v/{category_id}/{episode_id}")
async def video_episode(category_id: str, episode_id: str, range: Annotated[str | None, Header()] = None, if_range: Annotated[str | None, Header()] = None):
    anime = await Anime.instance()
    try:
        video = await anime.get_video(category_id, episode_id)
        if video is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Video {category_id}/{episode_id} not found")
        video_resp = await anime.open_video(video, range, if_range)
        headers = video_resp.headers.copy()
        headers.pop("Date")
        headers.pop("Server")
        tasks = BackgroundTasks()
        tasks.add_task(video_resp.wait_for_close)
        return StreamingResponse(
            video_resp.content.iter_any(),
            status_code=status.HTTP_206_PARTIAL_CONTENT,
            headers=headers,
            media_type=video_resp.content_type,
            background=tasks
        )
    except aiohttp.ClientResponseError as e:
        raise HTTPException(e.status, detail=e.message)
    except aiohttp.ClientConnectorError as e:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=e.strerror)


if __name__ == "__main__":
    uvicorn_config = uvicorn.Config(app="main:app", host="127.0.0.1", port=8000)
    uvicorn_server = uvicorn.Server(config=uvicorn_config)
    uvicorn_server.run()
