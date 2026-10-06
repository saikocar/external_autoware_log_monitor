from asyncio import sleep
from asyncio.subprocess import DEVNULL, create_subprocess_exec

from aiofiles.tempfile import NamedTemporaryFile
from aiohttp import ClientSession
from just_playback import Playback


async def text_to_speech(text: str) -> bytes:
    # 旧 www.google.com/async/translate_tts は2026-08時点で空応答を返すようになったため、
    # mp3を直接返すtw-obエンドポイントを使用 (User-Agent必須、テキストは200文字程度まで)
    endpoint = 'https://translate.google.com/translate_tts'
    parameters = {'ie': 'UTF-8', 'q': text, 'tl': 'ja', 'client': 'tw-ob'}
    headers = {'User-Agent': 'Mozilla/5.0'}

    async with ClientSession() as session:
        async with session.get(endpoint, params=parameters, headers=headers) as response:
            response.raise_for_status()
            return await response.read()


async def play_speech(text: str) -> None:
    async with (NamedTemporaryFile() as f1, NamedTemporaryFile(suffix='.mp3') as f2):
        raw_audio_data = await text_to_speech(text)
        if raw_audio_data == b'':
            return

        await f1.write(raw_audio_data)
        await (await create_subprocess_exec('ffmpeg', '-i', f1.name, '-af', 'atempo=1.5', f2.name, '-y', stderr=DEVNULL)).communicate()

        print('DEBUG: playing text-to-speech')
        playback = Playback(f2.name)
        playback.play()
        while playback.active:
            await sleep(0.01)
