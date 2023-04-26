import asyncio
from os import getenv
from typing import List
from aiohttp import web, ClientSession
from contextvars import ContextVar

ADMIN_URL = getenv("ADMIN", "http://alice:3001")
settings: ContextVar[dict] = ContextVar("settings", default={})
websockets: ContextVar[List[web.WebSocketResponse]] = ContextVar("websockets")


routes = web.RouteTableDef()


@routes.post("/topic/{topic}/")
async def topic_handler(request):
    topic = request.match_info["topic"]
    payload = await request.json()
    print("Received from:", request.remote, topic, payload, flush=True)
    for ws in websockets.get():
        await ws.send_json({"topic": topic, "payload": payload})
    return web.Response(status=200)


@routes.get("/ws")
async def websocket_handler(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    print("New websocket connection", flush=True)
    await ws.send_json({"topic": "settings", "payload": settings.get()})
    try:
        websockets.get().append(ws)
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT:
                if msg.data == "close":
                    await ws.close()
            elif msg.type == web.WSMsgType.ERROR:
                print("ws connection closed with exception %s" % ws.exception())
    finally:
        websockets.get().remove(ws)

    return ws


async def get_settings():
    async with ClientSession() as session:
        async with session.get(ADMIN_URL + "/status") as resp:
            if resp.ok:
                return await resp.json()
            else:
                raise Exception("Could not get settings")


async def main():
    settings.set(await get_settings())
    websockets.set([])

    app = web.Application()
    app.add_routes(routes)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
