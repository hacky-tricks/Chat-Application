import json
from pydoc import text
from tkinter import font
from tkinter.tix import TList
from typing import Container, List, Tuple
from requests.api import delete
import websocket
import asyncio
import datetime
import threading
import os
import jwt
import requests,base64
import time
from tkinter import *
from tkinter import ttk
cd = os.path.dirname(os.path.realpath(__file__))
import re



class API:
    BASEURL = "http://localhost:5000"
    REGISTER_URL = BASEURL+"/register"
    LOGIN_URL = BASEURL+"/login"
    SEARCH_USERNAMES_URL = BASEURL+"/getusers"
    @staticmethod
    def register(fname,lname,uname,email,password):
        payload = {"fname":fname,"lname":lname,"uname":uname,"email":email,"password":password}
        response = requests.post(API.REGISTER_URL,json=payload).json()
        print(response)
        return response
    @staticmethod
    def login(uname,password):
        payload = {"uname":uname,"password":(base64.b64encode(password.encode("ascii"))).decode("ascii")}
        response = requests.post(API.LOGIN_URL,json=payload).json()
        print(response)
        return response
    @staticmethod
    def searchUsernames(authToken,uname):
        payload = {"username":uname}
        headers = {"Authorization":f"Bearer {authToken}"}
        response = requests.post(API.SEARCH_USERNAMES_URL,headers=headers,json=payload).json()
        return response


class ClientUser:
    def __init__(self,authToken=None) -> None:
        
        data:dict = jwt.decode(authToken,"myFavKey","HS256")
        self.first_name = data.get("first_name")
        self.last_name = data.get("last_name")
        self.username = data.get("username")
        self.email = data.get("email")
        self.authToken:str = authToken
    def getAuth(self)->str:
        return self.authToken
    
class FriendUser:
    def __init__(self,fname,lname,uname) -> None:
        self.first_name:str = fname
        self.last_name:str = lname
        self.username:str = uname
   
class Message:
    @classmethod
    def getMessage(cls,message_obj):
        return cls(message_obj[0],message_obj[1],message_obj[2],message_obj[3],message_obj[4])
    def __init__(self,username=None,friend_username=None,message_id=None,is_seen=None,content=None) -> None:
        self.username = username
        self.friend_username = friend_username
        self.message_id = message_id
        self.is_seen = is_seen
        if self.is_seen == 0:
            self.is_seen = False
        if self.is_seen == 1:
            self.is_seen = True
        self.content = content
        
clientUser = ClientUser("eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJmaXJzdF9uYW1lIjoieWFzaCIsImxhc3RfbmFtZSI6Imd1cHRhIiwidXNlcm5hbWUiOiJ5YXNoMTE4IiwiZW1haWwiOiJ5Z3lndXB0YTBAZ21haWwuY29tIn0.UJW0FR9I5kkDjlMRQLLsfmtnHr2OZUiBjjzgXqjjPvg")


class WebsocketClient:
    url ="ws://localhost:1000"
    
    def __init__(self,container,url="ws://localhost:1000") -> None:
        self.ws = websocket.WebSocketApp(url,on_message=self.on_message,on_error=self.on_error)
        self.ws.on_close = self.on_close
        self.container:ChatWindow = container
    def connect(self):
        #self.ws.run_forever(ping_interval=3,ping_timeout=1)
        thread = threading.Thread(target=self.ws.run_forever,kwargs={"ping_interval":3,"ping_timeout":1})
        thread.start()
        
        
    def on_message(self,ws,message):
        try:
            message = json.loads(message)
        except Exception:
            return
        if message.get("eventType")=="active_chat_list":
            active_chat_list = message.get("active_chats")
            self.container.displayActiveChatList(active_chat_list)
        if message.get("eventType")=="get_friend_user":
            friend_user = message.get("friend_user")
            friend_object= FriendUser(friend_user.get("first_name"),friend_user.get("last_name"),friend_user.get("username"))
            self.container.active_chat_list_config["active_chat_friend_object"] = friend_object
            self.container.display_active_chat_header(friend_object)
        if message.get("eventType") == "load_message_history":
            chat_data = message.get("chat_data")
            try:
                chat_data = [Message().getMessage(message) for message in chat_data]
            
                self.container.loadChatMessages(chat_data)
            except Exception as e:
                print(str(e))
        if message.get("eventType") == "received_message":
            username=message.get("username")
            friend_username = message.get("friend_username")
            content = message.get("content")
            is_seen = message.get("is_seen")
            message_id = message.get("message_id")
            message = Message(username,friend_username,message_id,is_seen,content)
            self.container.add_chat_message(message)
            
    def on_error(self,ws,error):
        print(str(error))
    def on_close(self,ws,thrr,four):
        print("connection got closed")
    
    def createConnection(self,authToken:str):
        payload = {"eventType":"create_connection","authToken":authToken}
        self.ws.send(json.dumps(payload))
    
    def getActiveChatList(self,username):
        payload = {"eventType":"get_active_chat","username":username}
        self.ws.send(json.dumps(payload))
    def getFriendUser(self,username):
        payload = {"eventType":"get_friend_user","username":username}
        self.ws.send(json.dumps(payload))
    def loadMessageHistory(self,username,friend_username):
        payload = {"eventType":"load_message_history","username":username,"friend_username":friend_username}
        self.ws.send(json.dumps(payload))
    def send_message(self):
        message = self.container.message_type_box.get()
        username = self.container.clientUser.username
        friend_username = self.container.active_chat_list_config['active_chat_friend_object'].username
        payload = {"eventType":"send_message","username":username,"friend_username":friend_username,"content":message}
        self.ws.send(json.dumps(payload))
        
class ActiveChatHandler:
    def __init__(self,container) -> None:
        self.container:ChatWindow = container
    def chat_active_focus(self,active_chat_object):
        active_chat_object.config(fg = '#dcddde',bg="#4f545c")
    def on_focus_out(self,active_chat_object):
        active_chat_object.config(fg = '#b9bbbe',bg="#2f3136")
    def on_click(self,label_obj):
        for frame,label,friend in self.container.active_chat_list_objects:
            if label == label_obj:
                last_active_chat_object = self.container.active_chat_list_config['active_chat_object']
                last_active_chat_label = last_active_chat_object[1]
                last_active_chat_label.bind("<Enter>",func=lambda event:self.chat_active_focus(last_active_chat_label))
                last_active_chat_label.bind("<Leave>",func=lambda event:self.on_focus_out(last_active_chat_label))
                last_active_chat_label.bind("<Button-1>",func=lambda event:self.on_click(last_active_chat_label))
                last_active_chat_label.config(bg="#2f3136",fg="#fff")
                label_obj.unbind("<Enter>")
                label_obj.unbind("<Leave>")
                label_obj.unbind("<Button-1>")
                self.container.active_chat_list_config['active_chat_object'] = (frame,label,friend)
                self.container.display_active_chat((frame,label,friend))


class GUI:
    def __init__(self):
        self.Window = Tk()
        self.Window.withdraw()
        self.login = Toplevel(self.Window,bg="#2f3136")
        self.login.title("Login")
        self.login.resizable(width = False,height = False)
        self.login.configure(width = 400,height = 300)
        #login title label
        self.login_title = Label(self.login,fg="#fff",text = "Please login to continue",justify = CENTER,font = "Helvetica 10 bold",bg="#2f3136")
        self.login_title.place(relheight = 0.15,relx = 0.3,rely = 0.07)
        #username Label
        self.login_name_label = Label(self.login,bg="#2f3136",fg="#fff",text = "Username: ")
        self.login_name_label.place(relheight = 0.08,relx = 0.1,rely = 0.2)
        #username Text Input
        self.username_input = Entry(self.login,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0)
        self.username_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.30,rely = 0.2)
        self.username_input.focus()
        #password Label
        self.password_label = Label(self.login,bg="#2f3136",fg="#fff",text="Password: ")
        self.password_label.place(relheight = 0.08,relx=0.1,rely=0.3)
        #password Text Input
        self.password_input = Entry(self.login,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0,show="*")
        self.password_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.30,rely = 0.3)
        #login button
        self.login_button = Button(self.login,text="Login",bg="#4E5D94",fg="white",borderwidth=0,width=10,command=lambda:self.tryLogin(self.username_input.get(),self.password_input.get()))
        self.login_button.place(relx = 0.38,rely = 0.4)
        self.login_button.bind("<Return>",lambda:self.tryLogin(self.username_input.get(),self.password_input.get()))
        #register Label
        self.register_label = Label(self.login,bg="#2f3136",fg="#868a91",text = "Need an account? Register",justify = CENTER)
        self.register_label.place(relx=0.32,rely=0.5)
        self.register_label.bind("<Button-1>",self.callRegisterWindow)
        self.login.protocol("WM_DELETE_WINDOW",lambda:self.Window.destroy())
        self.clientUser = None
        self.chatWindow = None
        #running GUI loop
        self.Window.mainloop()
        
    def startChat(self,error_window:Toplevel):
        error_window.destroy()
        self.chatWindow = ChatWindow(self)
        self.chatWindow.createTopLevel()
    def tryLogin(self,uname:str,password:str):
        uname = uname.replace(" ","")
        password = password.replace(" ","")
        if uname == "" or password=="":
            error = "Invalid Input!"
            self.errorPopupWindow(error)
            return
        response = API.login(uname,password)
        if not response.get("authToken"):
            self.errorPopupWindow(response.get("error"))
            return
        authToken = response.get("authToken")
        self.clientUser = ClientUser(authToken)
        uname = self.clientUser.username
        fname = self.clientUser.first_name
        lname = self.clientUser.last_name
        email = self.clientUser.email
        
        errorWindow = Toplevel(bg="#2f3136")
        errorWindow.title("success")
        errorWindow.resizable(width = False,height = False)
        errorWindow.geometry("300x100")
        errorOk_label = Label(errorWindow,text="Login Successfully!",bg="#2f3136",fg="#fff",justify=CENTER)
        #errorOk_label.place(relheight = 0.15,relx = 0.3,rely = 0.07)
        errorOk_label.grid(row=0,padx=90,pady=15)
        errorOk_button = Button(errorWindow,text="ok",borderwidth=0,bg="#4E5D94",fg="#fff",command=lambda:self.startChat(errorWindow),width=10)
        #errorOk_button.place(relx = 0.45,rely = 0.2,width=40)
        errorOk_button.grid(row=1)
        self.login.destroy()
        
    def callRegisterWindow(self,event):
        self.login.withdraw()
        #self.Window.deiconify()
        self.registerWindow = Toplevel(self.Window,bg="#2f3136")
        self.registerWindow.title("Register")
        self.registerWindow.resizable(width = False,height = False)
        self.registerWindow.configure(width = 400,height = 300)
        self.registerWindow.protocol("WM_DELETE_WINDOW", self.LoginWindow)
        #login title label
        self.register_label_title = Label(self.registerWindow,text = "Create an account",fg="#fff",bg="#2f3136",justify = CENTER,font = "Helvetica 10 bold")
        self.register_label_title.place(relheight = 0.15,relx = 0.35,rely = 0.07)
        #first name Label
        self.first_name_label = Label(self.registerWindow,text = "First Name: ",fg="#fff",bg="#2f3136")
        self.first_name_label.place(relheight = 0.08,relx = 0.1,rely = 0.2)
        #first name Text Input
        self.first_name_input = Entry(self.registerWindow,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0)
        self.first_name_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.35,rely = 0.2)
        self.first_name_input.focus()
        #last name Label
        self.last_name_label = Label(self.registerWindow,text = "Last Name: ",fg="#fff",bg="#2f3136")
        self.last_name_label.place(relheight = 0.08,relx = 0.1,rely = 0.3)
        #last name Text Input
        self.last_name_input = Entry(self.registerWindow,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0)
        self.last_name_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.35,rely = 0.3)
        #username Label
        self.username_label = Label(self.registerWindow,text="Username: ",fg="#fff",bg="#2f3136")
        self.username_label.place(relheight = 0.08,relx=0.1,rely=0.4)
        #username Text Input
        self.username_input = Entry(self.registerWindow,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0,)
        self.username_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.35,rely = 0.4)
        #email Label
        self.email_label = Label(self.registerWindow,text="Email: ",fg="#fff",bg="#2f3136")
        self.email_label.place(relheight = 0.08,relx=0.1,rely=0.5)
        #email Text Input
        self.email_input = Entry(self.registerWindow,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0,)
        self.email_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.35,rely = 0.5)
        #password Label
        self.password_label = Label(self.registerWindow,text="Password: ",fg="#fff",bg="#2f3136")
        self.password_label.place(relheight = 0.08,relx=0.1,rely=0.6)
        #password Text Input
        self.password_input = Entry(self.registerWindow,font = "Helvetica 10",bg="#202225",fg="#72767d",borderwidth=0,)
        self.password_input.place(relwidth = 0.4,relheight = 0.08,relx = 0.35,rely = 0.6)
        #login button
        self.login_button = Button(self.registerWindow,bg="#4E5D94",fg="white",borderwidth=0,width=10,text="Register",command=lambda:self.register(self.first_name_input.get(),self.last_name_input.get(),self.username_input.get(),self.email_input.get(),self.password_input.get()))
        self.login_button.bind("<Return>",lambda:self.register(self.first_name_input.get(),self.last_name_input.get(),self.username_input.get(),self.email_input.get(),self.password_input.get()))
        self.login_button.place(relx = 0.43,rely = 0.7)
        #already account label
        self.already_label = Label(self.registerWindow,text="Already have an account?",bg="#2f3136",fg="#868a91")
        self.already_label.place(relwidth = 0.4,relheight = 0.08,relx = 0.3,rely = 0.8)
        self.already_label.bind("<Button-1>",self.LoginWindow)
        
    
    def errorPopupWindow(self,error):
        errorWindow = Toplevel()
        errorWindow.title("Error")
        errorWindow.resizable(width = False,height = False)
        errorWindow.geometry("300x100")
        #error label
        errorOk_label = Label(errorWindow,text=error,justify=CENTER)
        #errorOk_label.place(relheight = 0.15,relx = 0.3,rely = 0.07)
        errorOk_label.grid(row=0,padx=100,pady=15)
        errorOk_button = Button(errorWindow,text="ok",command=lambda:errorWindow.destroy(),width=10)
        #errorOk_button.place(relx = 0.45,rely = 0.2,width=40)
        errorOk_button.grid(row=1)
        
        
    def LoginWindow(self,event=None):
        self.registerWindow.destroy()
        self.login.deiconify()
    
    def register(self,fname:str,lname:str,uname:str,email:str,password:str):
        fname = fname.replace(" ","")
        lname = lname.replace(" ","")
        uname = uname.replace(" ","")
        email = email.replace(" ","")
        password = password.replace(" ","")
        if fname == "" or lname == "" or uname=="" or email== "" or password=="":
            error = "Invalid Input!"
            self.errorPopupWindow(error)
            return
        emailConditions = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        if not re.fullmatch(emailConditions, email):
            self.errorPopupWindow("Please enter a valid email address.")
        #self.login.deiconify()
        #self.registerWindow.destroy()
        response = API.register(fname,lname,uname,email,password)
        if response.get("errorCode")!=0:
            self.errorPopupWindow(response.get("error"))
        if response.get("status") == "success":
            errorWindow = Toplevel()
            errorWindow.title("success")
            errorWindow.resizable(width = False,height = False)
            errorWindow.geometry("300x100")
            #error label
            errorOk_label = Label(errorWindow,text="Registered Successfully!",justify=CENTER)
            #errorOk_label.place(relheight = 0.15,relx = 0.3,rely = 0.07)
            errorOk_label.grid(row=0,padx=90,pady=15)
            errorOk_button = Button(errorWindow,text="ok",command=lambda:errorWindow.destroy(),width=10)
            #errorOk_button.place(relx = 0.45,rely = 0.2,width=40)
            errorOk_button.grid(row=1)
            self.registerWindow.destroy()
            self.login.deiconify()

class ChatWindow:
    def __init__(self,master:GUI) -> None:
        #variables
        self.searchResultLabels:list[Label] = []
        self.search_result_current_rely = 0.36
        #chat list variables
        self.active_chat_list = []
        self.active_chat_list_config = {"first_active_chat_rely":0.2,"active_chat_pady":0.09,"current_active_chat_pady":0.2,"active_chat_object":None,"active_chat_friend_object":None}
        self.active_chat_list_objects:List[Tuple[Frame,Label,FriendUser]]= [] #each (frame,label,friendUser) objects
        self.active_chat_handler = ActiveChatHandler(self)
        self.master:GUI = master
        self.mainWindow:Tk = self.master.Window
        self.clientUser = master.clientUser
        self.websocketClient = WebsocketClient(self)
        self.websocketClient.connect()
        time.sleep(1)
        self.websocketClient.createConnection(self.clientUser.getAuth())
        
        
        
    def on_entry_click(self,event):
        """function that gets called whenever entry is clicked"""
        if self.search_box.get() == ' type username':
            self.search_box.delete(0,"end") # delete all the text in the entry
            self.search_box.insert(0, '') #Insert blank for user input
            self.search_box.config(fg = 'black')
            
    def on_focusout(self,event):
        if self.search_box.get() == '':
            self.search_box.insert(0, ' type username')
            self.search_box.config(fg = 'grey')
        
    def createTopLevel(self):
        self.chatApp = Toplevel(self.mainWindow,bg="#2f3136")
        self.chatApp.title("Chatting")
        self.chatApp.resizable(width = False,height = False)
        self.chatApp.protocol("WM_DELETE_WINDOW", self.chatWindowClose)
        #self.chatApp.configure(width = 700,height = 600)
        self.chatApp.geometry("900x600")
        self.style = ttk.Style()
        #chat names to chat box seperator
        separator = ttk.Separator(self.chatApp, orient=VERTICAL)
        separator.place(relx=0.24, rely=0, relheight=1)
        
        #chat box to username search seperator
        separator = ttk.Separator(self.chatApp, orient=VERTICAL)
        separator.place(relx=0.76, rely=0, relheight=1)
        self.__add_user_info_area()
        #search box
        self.__add_search_box()
        self.__add_active_chat_list_base()
        self.display_chat_name = Label(self.chatApp,bg="#2f3136",fg="#fff",height=2,font="Helvetica 11 bold")
        
        
    def __add_search_box(self):    
        
        self.search_box = Entry(self.chatApp,font = "Helvetica 10",relief=RAISED)
        self.search_box.config(fg = 'grey')
        self.search_box.insert(0," type username")
        self.search_box.place(relheight=0.035,relwidth = 0.18,relx = 0.79,rely = 0.23)
        self.search_box.bind("<FocusIn>",func=self.on_entry_click)
        self.search_box.bind("<FocusOut>",func=self.on_focusout)
        self.search_button = Button(self.chatApp,text="Search",bg="#4E5D94",fg="#FFFFFF",borderwidth=0,command=lambda:threading.Thread(target = self.updateUserSearchList, args = (self.search_box.get(),) ).start())
        self.search_button.place(relheight=0.035,relwidth = 0.18,relx = 0.79,rely = 0.27)
        self.search_btn_seperator = ttk.Separator(self.chatApp,orient=HORIZONTAL)
        self.search_btn_seperator.place(relx=0.76,relwidth=1,rely=0.33)
        self.no_result_label =Label(self.chatApp,font="Whitney 10 bold",text="No users found!",justify = CENTER,bg="#23272A",fg="#FFFFFF")
    
    
    def _add_search_result_label(self,uname):
        user_label = Label(self.chatApp,font="Whitney 10 bold",text=str(uname),bg="#23272A",fg="#FFFFFF")
        user_label.bind("<Button-1>",lambda event:self.createNewChat(uname))
        user_label.bind("<Enter>",lambda event:user_label.configure(font="Whitney 10 bold underline"))
        user_label.bind("<Leave>",lambda event:user_label.configure(font="Whitney 10 bold"))
        user_label.place(relheight=0.05,relx=0.85,rely=self.search_result_current_rely)#,relwidth=0.2)
        self.searchResultLabels.append(user_label)
        self.search_result_current_rely+=0.08
        
    def __add_user_info_area(self):
        self.name_label = Label(self.chatApp,font='Uni-Sans',text=f"{self.clientUser.first_name} {self.clientUser.last_name}",bg="#2f3136",fg="#fff")
        self.name_label.place(relheight=0.035,relwidth=0.18,relx=0.79,rely=0.03)
        self.username_label = Label(self.chatApp,font="Uni-Sans 10",text=f"{self.clientUser.username}",fg="#fff",bg="#2f3136")
        self.username_label.place(relheight=0.035,relwidth=0.18,relx=0.79,rely=0.07)
        self.logout_btn = Button(self.chatApp,text="Logout",bg="#ec3c3f",fg="white",borderwidth=0,width=10,command=lambda:self.logout(),padx=10)
        self.logout_btn.place(relheight=0.035,relwidth=0.18,relx=0.79,rely=0.13)
        self.user_info_seperator = ttk.Separator(self.chatApp,orient=HORIZONTAL)
        self.user_info_seperator.place(relx=0.76,rely=0.20,relwidth=1)
  
    def __add_active_chat_list_base(self):
        def on_entry():
            if self.find_conversation.get() == ' Find a conversation':
                self.find_conversation.delete(0,"end") # delete all the text in the entry
                self.find_conversation.insert(0, '') #Insert blank for user input
        def on_focusout():
            if self.find_conversation.get() == '':
                self.find_conversation.insert(0, ' Find a conversation')
        self.find_conversation = Entry(self.chatApp,font = "Helvetica 10",borderwidth=0)
        self.find_conversation.config(bg = '#202225',fg="#72767d")
        self.find_conversation.insert(0," Find a conversation")
        self.find_conversation.bind("<FocusIn>",func=lambda event:on_entry())
        self.find_conversation.bind("<FocusOut>",func=lambda event:on_focusout())
        self.find_conversation.place(relx=0.03,rely=0.04,relheight=0.043,relwidth=0.18)
        self.find_conversation_seperator = ttk.Separator(self.chatApp,orient=HORIZONTAL)
        #self.find_conversation_seperator.place(relwidth=0.24,rely=0.12)
        self.find_conversation_seperator.place(relwidth=0.76,rely=0.12)
        #self.find_conversation_seperator = Frame(self.chatApp,bg="blue")
        #self.find_conversation_seperator.place(rely=0.12,width=1)
        self.websocketClient.getActiveChatList(self.clientUser.username)
    
    def add_active_chat_event(self,label_obj):
        label_obj.bind("<Enter>",func=lambda event:self.active_chat_handler.chat_active_focus(label_obj))
        label_obj.bind("<Leave>",func=lambda event:self.active_chat_handler.on_focus_out(label_obj))
        label_obj.bind("<Button-1>",func=lambda event:self.active_chat_handler.on_click(label_obj))
    def add_active_chat_list_frame(self,active_chat,current_rely)->Tuple[Frame,Label]:
        obj = Frame(self.chatApp,bg="#2f3136",borderwidth=5,highlightbackground="#2f3136",height=1.5)
        obj.place(relx=0.12,rely=current_rely,anchor=CENTER)
        objLabel = Label(obj,text=active_chat,bg="#2f3136",fg="#b9bbbe",height=2,width=20,font="Helvetica 11 bold")
        #objLabel.place(relx=0.03,rely=current_rely,width=0.24)
        self.add_active_chat_event(objLabel)
        objLabel.grid(column=0,row=0,padx=5,pady=5)
        return (obj,objLabel)
    
    def resetActiveChatConfig(self):
        self.active_chat_list_config = {"first_active_chat_rely":0.2,"active_chat_pady":0.09,"current_active_chat_pady":0.2,"active_chat_object":None,"active_chat_friend_object":None}
    def displayActiveChatList(self,active_chat_list):
        self.active_chat_list = active_chat_list
        current_rely = self.active_chat_list_config['first_active_chat_rely']
        for active_chat in self.active_chat_list:
            obj = self.add_active_chat_list_frame(active_chat,current_rely)
            self.active_chat_list_objects.append((*obj,active_chat))
            self.active_chat_list_config["current_active_chat_pady"]+=self.active_chat_list_config["active_chat_pady"]
            current_rely = self.active_chat_list_config["current_active_chat_pady"]
        if len(self.active_chat_list_objects)!=0:
            self.display_active_chat(self.active_chat_list_objects[0])
            
            
    def display_active_chat_header(self,friendUser:FriendUser):
        self.display_chat_name.config(text=f"{friendUser.first_name} {friendUser.last_name}")
        self.display_chat_name.place(relx=0.255,rely=0.025)
        
    def add_chat_message(self,message:Message):
        self.chat_area.config(state="normal")
        if message.username == self.clientUser.username:
            author = "You"
        else:
            author = self.active_chat_list_config["active_chat_friend_object"].first_name
        self.chat_area.insert(END,f"     {author}:  ")
        self.chat_area.insert(END,f"{message.content}\n")
        self.chat_area.config(state="disabled")
    def display_active_chat(self,active_chat_object:Tuple[Frame,Label,str]):
        def on_entry():
            if self.message_type_box.get() == ' Type your message...':
                self.message_type_box.delete(0,"end") # delete all the text in the entry
                self.message_type_box.insert(0, '') #Insert blank for user input
        def on_focusout():
            if self.message_type_box.get() == '':
                self.message_type_box.insert(0, ' Type your message...')
        self.active_chat_list_config['active_chat_object'] = active_chat_object
        active_chat_object[1].config(fg = '#fff',bg="#4f545c")
        active_chat_object[1].unbind("<Enter>")
        active_chat_object[1].unbind("<Leave>")
        active_chat_object[1].unbind("<Button-1>")
        self.websocketClient.getFriendUser(active_chat_object[2])
        scrollbar = Scrollbar(self.chatApp,bg="#4a4849")
        scrollbar.place(rely=0.16,relx=0.74,height=431)
        self.chat_area = Text(self.chatApp,height = 13, width = 48,bg="#36393f",fg="#dcddde",font='Whitney,"Helvetica-Neue",Helvetica,Arial,sans-serif',bd=0,highlightthickness=0.1,relief='ridge',state="disabled",wrap=NONE,yscrollcommand=scrollbar.set,spacing1=15)
        scrollbar.config(command=self.chat_area.yview)
        self.chat_area.place(rely=0.16,relx=0.255)
        self.websocketClient.loadMessageHistory(self.clientUser.username,self.active_chat_list_config['active_chat_object'][2])
        
        self.message_type_box = Entry(self.chatApp,font = "Helvetica 10",borderwidth=0,bg = '#202225',fg="#72767d")
        self.message_type_box.insert(0," Type your message...")
        self.message_type_box.bind("<FocusIn>",func=lambda event:on_entry())
        self.message_type_box.bind("<FocusOut>",func=lambda event:on_focusout())
        self.message_type_box.place(relx=0.255,rely=0.9,height=40,width=365)
        self.message_send_btn = Button(self.chatApp,command=lambda:threading.Thread(target=self.send_message).start(),font="Helvetica 10 bold",text="Send",bg="#b9bbbe",fg="#4f545c",borderwidth=0,width=10,padx=10)
        self.message_send_btn.place(height=40,relwidth=0.08,relx=0.67,rely=0.9)
    
    def send_message(self):
        print("called")
        if self.message_type_box.get() == '':
                self.message_type_box.insert(0, ' Type your message...')
                return
        if self.message_type_box.get() == ' Type your message...':
            return
        try:
            self.websocketClient.send_message()
        except Exception as e:
            print(str(e))
        self.message_type_box.delete(0,"end")
        self.message_type_box.insert(0, ' Type your message...')
    
    def loadChatMessages(self,chat_data):
        for message in chat_data:
            self.add_chat_message(message)
    
    def logout(self):
        self.chatApp.destroy()
        self.mainWindow.destroy()
        self.websocketClient.ws.close()
    
    def updateUserSearchList(self,uname):
        response = API.searchUsernames(self.clientUser.authToken, uname)
        users = response.get("usernames")
        if len(users)==0:
            self.no_result_label.place(relheight=0.05,relwidth=0.2,relx=0.78,rely=0.36)
            for label in self.searchResultLabels:
                label.destroy()
            self.searchResultLabels.clear()
            return
        if self.no_result_label.winfo_ismapped():
            self.no_result_label.place_forget()
        
        for label in self.searchResultLabels:
            label.destroy()
        self.searchResultLabels.clear()
        self.search_result_current_rely = 0.36
        for user in users:
            self._add_search_result_label(user)
            
    def createNewChat(self,uname):
        
        for frame,label,username in self.active_chat_list_objects:
            print(username,self.active_chat_list_config['active_chat_object'][2])
            if uname == self.active_chat_list_config['active_chat_object'][2]:
                return
            if username == uname:
                last_active_chat_object = self.active_chat_list_config['active_chat_object']
                last_active_chat_label = last_active_chat_object[1]
                last_active_chat_label.bind("<Enter>",func=lambda event:self.active_chat_handler.chat_active_focus(last_active_chat_label))
                last_active_chat_label.bind("<Leave>",func=lambda event:self.active_chat_handler.on_focus_out(last_active_chat_label))
                last_active_chat_label.bind("<Button-1>",func=lambda event:self.active_chat_handler.on_click(last_active_chat_label))
                last_active_chat_label.config(bg="#2f3136",fg="#fff")
                label.unbind("<Enter>")
                label.unbind("<Leave>")
                label.unbind("<Button-1>")
                self.active_chat_list_config['active_chat_object'] = (frame,label,username)
                self.display_active_chat((frame,label,username))
                return
        self.active_chat_list.insert(0,uname)
        self.active_chat_list_objects.clear()
        self.resetActiveChatConfig()
        self.displayActiveChatList(self.active_chat_list)
    
    def chatWindowClose(self):
        self.chatApp.destroy()
        self.mainWindow.destroy()
        self.websocketClient.ws.close()
        
if __name__ == "__main__":
    g = GUI()