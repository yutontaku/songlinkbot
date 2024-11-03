from aiogram import Bot, types, Dispatcher, executor
from aiohttp import ClientSession
import asyncio
import json
from functools import wraps, partial
from songlink_config import token
import hashlib
import re
import aiogram.utils.markdown as md


loop = asyncio.get_event_loop()
bot = Bot(token=token, loop=loop)
dp = Dispatcher(bot)


def run_async(func):
    @wraps(func)
    async def run(*args, loop=None, executor=None, **kwargs):
        if loop is None:
            loop = asyncio.get_event_loop()
        pfunc = partial(func, *args, **kwargs)
        return await loop.run_in_executor(executor, pfunc)
    return run


class SongLink():
    async def get_links(self):
        async with ClientSession() as session:
            async with session.get(f"https://api.song.link/v1-alpha.1/links?url={self.link}") as response:
                return await response.text()


    @run_async
    def parse_links(self, song_link):
        self.link = song_link
        to_parse = asyncio.run(self.get_links())
        parsed = json.loads(to_parse)
        pattern = r"[a-zA-Z0-9]+_[VIDEO\SONG]+::[a-zA-Z0-9]+"
        regex = re.compile(pattern)
        match = regex.search(json.dumps(parsed, indent=4))
        out = list()
        return parsed["entitiesByUniqueId"][match.group()]['title'], parsed["entitiesByUniqueId"][match.group()]['artistName'], parsed['pageUrl'], parsed["linksByPlatform"]


@dp.inline_handler()
async def inline_song(inline_query: types.InlineQuery):
    text = inline_query.query
    input_content = types.InputTextMessageContent(text)
    result_id: str = hashlib.md5(text.encode()).hexdigest()
    regex = re.compile(r'''((?:https://)[^ <>'"{}|\\^`[\]]*)''')
    if regex.search(input_content.message_text) is not None:
        songlink = SongLink()
        song_title, song_artist, song_url, platforms = await songlink.parse_links(input_content.message_text)
        platform_buttons = types.InlineKeyboardMarkup()
        temp_buttons = list()
        for platform in zip(['yandex', 'appleMusic', 'spotify'], ['Yandex Music', 'Apple Music', 'Spotify']):
            try:
                temp_buttons.append(types.InlineKeyboardButton(platform[1], platforms[platform[0]]['url']))
            except:
                pass
        platform_buttons.add(*temp_buttons)
        try:
            platform_buttons.add(types.InlineKeyboardButton('Youtube Music', url=platforms['youtubeMusic']['url']))
        except:
            pass
        output_content = types.InputTextMessageContent(md.text(
                                                    md.text(f"{song_title} by {song_artist}"),
                                                    md.text(song_url),
                                                    sep='\n',
                                                ), disable_web_page_preview=True)
        item = types.InlineQueryResultArticle(id=result_id, title='Get song.link', input_message_content=output_content, reply_markup=platform_buttons)
    else:
        output_content = types.InputTextMessageContent('I need a link to the song to work with!')
        item = types.InlineQueryResultArticle(id=result_id, title='Paste a link to song',
                                              input_message_content=output_content)
    await bot.answer_inline_query(inline_query.id, results=[item], cache_time=1)


if __name__ == '__main__':
    executor.start_polling(dp, loop=loop, skip_updates=True)
