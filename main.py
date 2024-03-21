from typing import List
import asyncio
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, WebSocket, Request, WebSocketDisconnect
import requests
from config import blogsCollection
import datetime
import pytz
app = FastAPI()
templates = Jinja2Templates(directory="templates")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept() #hand
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str, websocket: WebSocket):
        for connection in self.active_connections:
            if connection == websocket:
                continue
            await connection.send_text(message)

connection_manager = ConnectionManager()

@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await connection_manager.send_personal_message(f"You: {data}", websocket)
            await connection_manager.broadcast(f"Someone: {data}", websocket)  # Change the message format here
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        await connection_manager.broadcast("Someone left the chat")  # Change the message here

async def send_hello():
    while True:
        await asyncio.sleep(5)
        for connection in connection_manager.active_connections:
            await connection.send_text("hello")

async def view_insert_db():
    while True:
        await asyncio.sleep(5)
        data = await send_post_request()
        if data is not None:
            for item in data['all_data']:
                # Format data
                formatted_data = {key: value for key, value in item.items()}
                vn_timezone = pytz.timezone('Asia/Ho_Chi_Minh')
                formatted_data['inserted_at'] = datetime.datetime.now(vn_timezone)
                
                # Insert data into MongoDB
                try:
                    insert_result = blogsCollection.insert_one(formatted_data)
                    print(f"Inserted document with _id: {insert_result.inserted_id}")
                except Exception as e:
                    print("Error inserting data into MongoDB:", e)

                # Send formatted data to WebSocket connections
                formatted_message = "\n".join([f"{key}: {value}" for key, value in formatted_data.items()])
                for connection in connection_manager.active_connections:
                    await connection.send_text(formatted_message)
async def send_post_request():
    url = "http://123.16.53.91:22102/api/validemo/get_all_data"
    while True:
        try:
            response = requests.post(url)
            response_data = response.json()
            # print("Received data from server:", response_data)
            return response_data
        except Exception as e:
            print("Error sending POST request:", e)
        await asyncio.sleep(5)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(view_insert_db())
    asyncio.create_task(send_post_request())  