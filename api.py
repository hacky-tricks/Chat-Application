import random
from types import resolve_bases
from discord import user
from flask import Flask, request, current_app
from flask_restful import Api
from flask_restful import Resource
import os
import json
import base64
import ssl
import requests
import hashlib
import jwt
import sqlite3
import datetime
cd = os.path.dirname(os.path.realpath(__file__))
app = Flask(__name__)
api = Api(app)

class Database:
    def __init__(self) -> None:
        self.db_name = "database.db"
        self.cd = os.path.dirname(os.path.realpath(__file__))
        self.con = sqlite3.connect(self.cd+'\\database.db', check_same_thread=False)
        self.cur = self.con.cursor()
        
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
        if uname:
            response = self.cur.execute(f"SELECT * from users WHERE username like '{uname}%'").fetchall()
        if email:
            response = self.cur.execute(f"SELECT * from users WHERE email like '{email}%'").fetchall()
        count = 0
        users = []
        for user in response:
            count+=1
            users.append(user)
            if count==5:
                break
        return users
    def getUserByValue(self,column,value)->tuple:
        response = self.cur.execute(f"SELECT * from users WHERE {column}='{value}'").fetchone()
        return response
db = Database()

    
class register(Resource):
    def post(self):
        if request.is_json is False:
            data = {"error":"Paremeters Missing."}
            return data
        content= request.get_json()
        mustneed = ["fname","lname","uname","email","password"]
        for query in mustneed:
            if not content.get(query):
                return {"error":400,"message":f"{query} parameter missing."}
        fname = content.get("fname")
        lname = content.get("lname")
        uname = content.get("uname").lower()
        email = content.get("email")
        password = content.get("password")
        if db.getUser(uname):
            return {"error":f"username '{uname}' already exists.","errorCode":1}
        if db.getUser(email=email):
            return {"error":f"email '{email}' already exists.","errorCode":2}
        authToken = jwt.encode({"first_name":fname,"last_name":lname,"username":uname,"email":email},"myFavKey","HS256")
        user = {"first_name":fname,"last_name":lname,"username":uname,"email":email,"password":password,"authToken":authToken}
        db.addUser(fname,lname,uname,email,password,authToken)
        return {"status":"success","errorCode":0}
        
api.add_resource(register, "/register")

class login(Resource):
    def post(self):
        if request.is_json is False:
            data = {"error":"Paremeters Missing."}
            return data
        content= request.get_json()
        mustneed = ["uname","password"]
        for query in mustneed:
            if not content.get(query):
                return {"error":400,"message":f"{query} parameter missing."}
        uname = content.get("uname")
        password = content.get("password")
        password = (base64.b64decode(password.encode("ascii"))).decode("ascii")
        
        user = db.getUser(uname)
        if not user:
            return {"error":f"username '{uname}' does not exists.","errorCode":3}
        if password != user[4]:
            return {"error":f"Password does not match.","errorCode":4}
        return {"authToken":user[5]}

api.add_resource(login,"/login")

class getusers(Resource):
    def post(self):
        Authorization = request.headers.get("authorization")
        if not Authorization:
            return {"status":False,"message":"Invalid Auth Token.","errorCode":401}
        response = db.getUserByValue("authToken",Authorization.split(" ")[1])
        if not response:
            return {"status":False,"message":"Invalid Auth Token.","errorCode":401}
        if request.is_json is False:
            data = {"error":"Paremeters Missing."}
            return data
        content= request.get_json()
        if not content.get("username"):
            return {"error":400,"message":f"username parameter missing."}
        username = content.get("username")
        users = db.getUsers(username)
        users = [user[2] for user in users]
        if response[2] in users:
            users.remove(response[2])
        return {"status":"success","errorCode":0,"usernames":users}

api.add_resource(getusers,"/getusers")

if __name__ == '__main__':
    
    app.run(debug=True,host="localhost")
    
    
