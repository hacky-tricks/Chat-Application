import json
from typing import ChainMap
import websockets
from websockets import server
import asyncio
import datetime
import threading
import sqlite3
import os
import jwt
cd = os.path.dirname(os.path.realpath(__file__))


class Database:
    def __init__(self) -> None:
        self.db_name = "database.db"
        self.cd = os.path.dirname(os.path.realpath(__file__))
        self.con = sqlite3.connect(self.cd+'\\database.db', check_same_thread=False)
        self.cur = self.con.cursor()
        
    def getCursor(self):
        return self.cur
        
    def createDatabase(self):
        self.cur.execute('''CREATE TABLE users
                (first_name text, 
                last_name text, 
                username text PRIMARY KEY, 
                email text, 
                password text, 
                authToken text)''')
        
    def getUser(self,uname=None,email=None):
        if uname:
            response = self.cur.execute(f"SELECT * from users WHERE username='{uname}'").fetchone()
        if email:
            response = self.cur.execute(f"SELECT * from users WHERE email='{email}'").fetchone()
        return response
    def addUser(self,fname,lname,uname,email,password,authToken):
        self.cur.execute(f"INSERT INTO users VALUES ('{fname}','{lname}','{uname}','{email}','{password}','{authToken}')")
        self.con.commit()
    def getUsers(self,uname=None,email=None):
        pass
    def searchUser(self,uname):
        response = self.cur.execute(f"SELECT * from users WHERE username like '{uname}%'").fetchall()
        return response
    
    def getUserByValue(self,column,value)->tuple:
        response = self.cur.execute(f"SELECT * from users WHERE {column}='{value}'").fetchone()
        return response
    
    def getActiveChat(self,username)->list:
        response1 = self.cur.execute(f"SELECT DISTINCT friend_username from chat_data where username='{username}'").fetchall()
        response1 = [data[0] for data in response1]
        response2 = self.cur.execute(f"SELECT DISTINCT username from chat_data where friend_username='{username}'").fetchall()
        response2 = [data[0] for data in response2]
        for username in response2:
            if username in response1: response2.remove(username)
        response = [*response1,*response2]
        return response
    
    def execute(self,query:str,commit=False):
        response = self.cur.execute(query)
        if commit is True:
            self.con.commit()
        return response
    
    
db = Database()


class Message():
    def __init__(self,username:str,content:str,timestamp:datetime.datetime = datetime.datetime.now()) -> None:
        self.username = username
        self.content = content
        self.timestamp = timestamp
        
class User:
    def __init__(self,authToken=None) -> None:
        
        data:dict = jwt.decode(authToken,"myFavKey","HS256")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")
        self.email = data.get("email")
        self.authToken:str = authToken
        
    def getAuth(self)->str:
        return self.authToken
    
connections = []
        
async def eventHandler(websocket,message):
    global connections
    try:
        message = json.loads(message)
    except Exception:
        return
    if message.get("eventType")=="create_connection":
        authToken = message.get("authToken")
        if not authToken:
            payload = {"error":"Invalid Auth Token.","errorCode":401}
            await websocket.send(json.dumps(payload))
            return 
        userResponse = db.getUserByValue("authToken",authToken)
        if not userResponse:
            payload = {"error":"Invalid Auth Token.","errorCode":401}
            await websocket.send(json.dumps(payload))
            return 
        user = User(authToken)
        connections.append((user,websocket))
        payload = {"eventType":"connection_success","errorCode":201}
        await websocket.send(json.dumps(payload))
        
    #get active chat list event
    if message.get("eventType")=="get_active_chat":
        username = message.get("username")
        if not username:
            payload = {"error":"Username Missing","errorCode":400}
            await websocket.send(json.dumps(payload))
            return
        response = db.getActiveChat(username)
        payload = {"eventType":"active_chat_list","active_chats":response}
        print(payload)
        await websocket.send(json.dumps(payload))
        return
    if message.get("eventType") == "load_message_history":
        username = message.get("username")
        friend_username = message.get("friend_username")
        data1 = db.execute(f"SELECT * FROM chat_data where username='{username}' and friend_username='{friend_username}'").fetchall()
        data2 =db.execute(f"SELECT * FROM chat_data where username='{friend_username}' and friend_username='{username}'").fetchall()
        chat_data = [*data1,*data2]
        chat_data.sort(key = lambda message_id: message_id[2])
        payload = {"eventType":"load_message_history","chat_data":chat_data}
        await websocket.send(json.dumps(payload))
        return
        
    if message.get("eventType") == "get_friend_user":
        username = message.get("username")
        response = db.getUser(username)
        payload = {"eventType":"get_friend_user","friend_user":{"first_name":response[0],"last_name":response[1],"username":response[2]}}
        
        await websocket.send(json.dumps(payload))
        return
    
    if message.get("eventType") == "send_message":
        username = message.get("username")
        friend_username = message.get("friend_username")
        content = message.get("content")
        response1 = db.execute(f"SELECT max(message_id) from chat_data where username='{username}' and friend_username='{friend_username}'").fetchall()
        response2 = db.execute(f"SELECT max(message_id) from chat_data where username='{friend_username}' and friend_username='{username}'").fetchall()
        if not response1[0][0]:
            response1 = [(0,)]
        if not response2[0][0]:
            response2 = [(0,)]
        message_id = max(response1[0],response2[0])[0]
        if not message_id:
            message_id = 0
            db.execute(f"INSERT into active_chat VALUES('{username}','{friend_username}')",commit=True)
        else:
            message_id = message_id + 1
        db.execute(f"INSERT into chat_data VALUES('{username}','{friend_username}','{message_id}',0,'{content}')",commit=True)
        payload = {"eventType":"received_message","username":username,"friend_username":friend_username,"content":content,"is_seen":False,"message_id":message_id}
        await websocket.send(json.dumps(payload))
        return
    
async def unregister(websocket):
    global connections
    for user,userWebsocket in connections:
        if websocket == userWebsocket:
            connections.remove((user,userWebsocket))
            break
    print("success")

async def webserver(websocket, path):
    while True:
        try:
            message = await websocket.recv()
            print(message)
            await eventHandler(websocket,message)
        except websockets.ConnectionClosed:
            await unregister(websocket)
            print(f"1 Session closed")
            break


start_server = server.serve(webserver, "localhost",1000)#"172.31.45.34", 1235)
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
print("Server is up!")
