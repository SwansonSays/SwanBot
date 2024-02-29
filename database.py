from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os

class DataBase():
    def __init__(self) -> None:
        load_dotenv()
        DB_ID = os.getenv("DB_ID")
        DB_KEY = os.getenv("DB_KEY")

        #Connect to DB
        uri = f"mongodb+srv://{DB_ID}:{DB_KEY}@cluster0.nvkklff.mongodb.net/?retryWrites=true&w=majority"
        cluster = MongoClient(uri, server_api=ServerApi('1'))
        # Send a ping to confirm a successful connection
        try:
            cluster.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)


        db = cluster["swanbot"]
        self.collection = db["money"]

    async def add_balance(self, id, value: int) -> int:
        balance = await self.get_balance(id)
        new_balance = balance + value
        await self.set_balance(id, new_balance)
        return new_balance


    async def get_balance(self, id) -> int:
        user = await self.get_user(id)
        for result in user:
            balance = result["money"]
        return balance


    async def set_balance(self, id, balance: int):
        self.collection.update_one({"_id": id}, {"$set":{"money": balance}})


    async def add_user(self, id) -> bool:
        myquery = {"_id": id}
        if(not await self.is_user(id)):
            post = {"_id": id, "money": 1000, "join_time": 0}
            self.collection.insert_one(post)
            return True
        print(f"{id} is already in database")
        return False


    async def is_user(self, id) -> bool:
        query = {"_id": id}
        if(self.collection.count_documents(query) == 0):
            return False
        return True


    async def get_user(self, id):
        query = {"_id": id}
        user = self.collection.find(query)
        return user


    async def set_join_time(self, id, join_time):
        self.collection.update_one({"_id": id}, {"$set":{"join_time": join_time}})


    async def getJoinTime(self, id):
        user = await self.get_user(id)
        for result in user:
            join_time = result["join_time"]
        return join_time