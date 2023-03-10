# Comment the history of the creator in comments.
# Make a function to get history of the creator and return final message as a string.

import pymongo
import re
import asyncio

def create_table_from_list(l):
    final_string=""
    for i in range(len(l)):
        row="|"
        for j in range(len(l[i])):
            row+=str(l[i][j])+"|"
        row+='\n'
        if i==0:
            row+=":--|"*(j+1)
            row+='\n'
        final_string+=row
    return final_string

mongo_uri="mongodb+srv://root:root@cluster.if4vaf9.mongodb.net/?retryWrites=true&w=majority"
mongo_dbname="reddit"
mongo_collection="transactions"
collection = pymongo.MongoClient(mongo_uri)[mongo_dbname][mongo_collection]

def get_info(s):
    result = re.findall('\(.*?\)', s)
    return result

def handle_new_post(user_id):
    o = f'Here is information on {user_id}\n\n'
    l = [ ["Borrower","Lender","Amount Requested","Amount Given","Given","Amount Repaid","Repaid","Orignal Thread","Date Given","Date Repaid"] ]
    myquery = {'Borrower': user_id}
    requester_doc = collection.find(myquery)
    for i in requester_doc:
            row = []
            for j in l[0]:
                row.append(i[j])
            l.append(row)
    myquery = {'Lender': user_id}
    lender_doc = collection.find(myquery)
    for i in lender_doc:
            row = []
            for j in l[0]:
                row.append(i[j])
            l.append(row)
    o += create_table_from_list(l)
    return o

if __name__ == "__main__":
    u = "Fit-Belt1935"
    handle_new_post(u)